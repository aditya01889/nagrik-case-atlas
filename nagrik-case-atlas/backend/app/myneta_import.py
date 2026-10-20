"""One-time, source-linked import of the 2024 Lok Sabha winners' ADR/MyNeta affidavit profiles.

This is a historical baseline, not a live court-status feed. Rows are marked source-matched
only when the profile page was fetched and the case-row count matches the published summary.
A source match is not a finding of guilt or an independent court-record verification.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import deque
from datetime import date
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import Constituency, Person, Party, Candidacy, CaseRecord, CasePersonLink, SourceDocument

log = logging.getLogger("nagrik_case_atlas.myneta_import")
BASE = "https://www.myneta.info/LokSabha2024/"
WINNERS_URL = BASE + "index.php?action=show_winners&sort=candidate"
SNAPSHOT_DATE = date(2024, 6, 4)
STATUS = {"state": "idle", "started_at": None, "finished_at": None, "candidates_seen": 0,
          "candidates_imported": 0, "case_rows_imported": 0, "needs_review": 0, "error": None}
_LOCK = threading.Lock()


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-") or "unknown"


def text(node) -> str:
    return " ".join(node.stripped_strings).strip() if node else ""


def integer(value):
    m = re.search(r"\d[\d,]*", value or "")
    return int(m.group(0).replace(",", "")) if m else None


def profile_id(url: str) -> str | None:
    m = re.search(r"candidate_id=(\d+)", url)
    return m.group(1) if m else None


def canonical_page(url: str) -> str:
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    # Preserve only the winners-list parameters that identify a page.
    params = {k: v[-1] for k, v in q.items() if k in {"action", "sort", "page"}}
    params.setdefault("action", "show_winners")
    params.setdefault("sort", "candidate")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", urlencode(params), ""))


def parse_winner_rows(soup: BeautifulSoup):
    found = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        link = row.find("a", href=re.compile(r"candidate\.php\?candidate_id=\d+"))
        if not link:
            continue
        href = urljoin(BASE, link.get("href", ""))
        pid = profile_id(href)
        if not pid:
            continue
        cell_texts = [text(c) for c in cells]
        try:
            name_idx = next(i for i, c in enumerate(cells) if c.find("a", href=re.compile(r"candidate\.php\?candidate_id=\d+")))
        except StopIteration:
            continue
        # MyNeta winner table: serial, candidate, constituency, party, declared-case count, education...
        name = text(link)
        constituency = cell_texts[name_idx + 1] if len(cell_texts) > name_idx + 1 else ""
        party = cell_texts[name_idx + 2] if len(cell_texts) > name_idx + 2 else ""
        declared = integer(cell_texts[name_idx + 3]) if len(cell_texts) > name_idx + 3 else None
        if name and constituency and party and declared is not None:
            found.append({"profile_id": pid, "name": name, "constituency": constituency,
                          "party": party, "declared_count": declared, "url": href})
    return found


def fetch_winners(client: httpx.Client):
    queue = deque([WINNERS_URL])
    visited = set()
    winners = {}
    while queue and len(visited) < 50:
        url = canonical_page(queue.popleft())
        if url in visited:
            continue
        visited.add(url)
        response = client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for item in parse_winner_rows(soup):
            winners[item["profile_id"]] = item
        for anchor in soup.find_all("a", href=True):
            href = urljoin(url, anchor["href"])
            parsed = urlparse(href)
            if parsed.netloc.lower() not in {"www.myneta.info", "myneta.info"}:
                continue
            q = parse_qs(parsed.query)
            if q.get("action", [""])[0] == "show_winners" and "page" in q:
                next_url = canonical_page(href)
                if next_url not in visited:
                    queue.append(next_url)
        time.sleep(0.5)
    if len(winners) < 450:
        raise RuntimeError(f"Expected at least 450 source-linked Lok Sabha 2024 winner profiles; found {len(winners)} across {len(visited)} list pages. Import marker was not written.")
    return list(winners.values())


def parse_profile(soup: BeautifulSoup):
    all_text = text(soup)
    m = re.search(r"Number of Criminal Cases\s*:\s*([\d,]+)", all_text, re.I)
    declared = int(m.group(1).replace(",", "")) if m else None
    state = None
    constituency = None
    for h in soup.find_all(["h4", "h5", "h6"]):
        value = text(h)
        match = re.match(r"(.+?)\s*\(([^()]+)\)\s*$", value)
        if match and len(value) < 140 and not re.search(r"criminal|asset|education|detail", value, re.I):
            constituency, state = match.group(1).strip(), match.group(2).strip()
            break
    cases = []
    seen = set()
    for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
        label = text(heading)
        if not re.search(r"Cases\s+where\s+(Pending|Convicted)", label, re.I):
            continue
        section = "Pending" if re.search(r"Pending", label, re.I) else "Convicted"
        table = heading.find_next("table")
        if not table:
            continue
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"], recursive=False)
            vals = [text(c) for c in cells]
            if len(vals) < 3 or all(c.name == "th" for c in cells):
                continue
            if re.search(r"^serial\s*no|^fir\s*no|^case\s*no", " ".join(vals), re.I):
                continue
            if not any(vals):
                continue
            # Ignore non-case summary tables that may follow a heading on malformed pages.
            if len(vals) < 4:
                continue
            key = (section, tuple(vals))
            if key in seen:
                continue
            seen.add(key)
            # Common MyNeta columns: serial, FIR, case number, court, IPC/BNS, other acts,
            # charges framed, date charges framed, appeal/present status.
            fir = vals[1] if len(vals) > 1 else ""
            case_no = vals[2] if len(vals) > 2 else ""
            court = vals[3] if len(vals) > 3 else ""
            provisions = vals[4] if len(vals) > 4 else ""
            other_acts = vals[5] if len(vals) > 5 else ""
            charges_framed = vals[6] if len(vals) > 6 else ""
            charges_date = vals[7] if len(vals) > 7 else ""
            appeal_status = vals[8] if len(vals) > 8 else ""
            detail_parts = [
                f"Disclosure section: Cases where {section}",
                f"FIR as transcribed: {fir}" if fir else "",
                f"Case number as transcribed: {case_no}" if case_no else "",
                f"IPC/BNS sections as transcribed: {provisions}" if provisions else "",
                f"Other acts/sections as transcribed: {other_acts}" if other_acts else "",
                f"Charges framed field: {charges_framed}" if charges_framed else "",
                f"Date charges framed field: {charges_date}" if charges_date else "",
                f"Appeal/present-status field as disclosed: {appeal_status}" if appeal_status else "",
                "Source is an ADR/MyNeta candidate-affidavit profile; allegations are not findings of guilt."
            ]
            cases.append({"section": section, "serial": vals[0], "fir": fir, "case_no": case_no,
                          "court": court, "provisions": provisions, "other_acts": other_acts,
                          "summary": "; ".join(p for p in detail_parts if p)})
    return {"declared_count": declared, "state": state, "constituency": constituency, "cases": cases}


def import_once():
    with _LOCK:
        if STATUS["state"] == "running":
            return
        STATUS.update(state="running", started_at=date.today().isoformat(), finished_at=None, error=None)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.get(SourceDocument, "bootstrap-myneta-ls2024-complete"):
            STATUS.update(state="complete", finished_at=date.today().isoformat())
            return
    finally:
        db.close()

    imported = 0
    case_rows = 0
    review = 0
    try:
        headers = {"User-Agent": "NagrikCaseAtlas/0.1 (public-interest research; contact via GitHub repository)"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            winners = fetch_winners(client)
            STATUS["candidates_seen"] = len(winners)
            for idx, winner in enumerate(winners, start=1):
                pid = winner["profile_id"]
                profile_url = winner["url"]
                try:
                    response = client.get(profile_url)
                    response.raise_for_status()
                    parsed = parse_profile(BeautifulSoup(response.text, "html.parser"))
                    page_name = None
                    for h in BeautifulSoup(response.text, "html.parser").find_all("h2"):
                        if text(h) and len(text(h)) < 160:
                            page_name = text(h)
                            break
                    name = winner["name"]
                    state = parsed["state"] or "Unknown state"
                    constituency = parsed["constituency"] or winner["constituency"]
                    declared = parsed["declared_count"]
                    rows = parsed["cases"]
                    exact = declared is not None and len(rows) == declared
                    if declared is None:
                        review += 1
                    elif not exact:
                        review += 1
                    status = "verified" if exact else "needs_review"
                    source_id = f"myneta-ls2024-source-{pid}"
                    person_id = f"myneta-ls2024-person-{pid}"
                    party_id = f"party-{slug(winner['party'])}"
                    constituency_id = f"lok_sabha:{slug(state)}:{slug(constituency)}"
                    notes = ("Automated source match against the candidate's ADR/MyNeta 2024 affidavit profile. "
                             "Not independently cross-checked against the original ECI affidavit or current court records. "
                             f"Summary declares {declared if declared is not None else 'an unknown number of'} cases; "
                             f"{len(rows)} case rows parsed. Status: {'row count matched' if exact else 'manual review required'}.")
                    db = SessionLocal()
                    try:
                        source = db.get(SourceDocument, source_id)
                        if not source:
                            source = SourceDocument(id=source_id, title=f"Lok Sabha 2024 affidavit profile — {name}",
                                source_type="adr_myneta_candidate_affidavit", source_url=profile_url,
                                published_date=None, verification_status="verified", reviewer="automated-source-match",
                                review_notes=notes)
                            db.add(source)
                        else:
                            source.title = f"Lok Sabha 2024 affidavit profile — {name}"
                            source.source_url = profile_url
                            source.verification_status = "verified"
                            source.reviewer = "automated-source-match"
                            source.review_notes = notes
                        party = db.get(Party, party_id)
                        if not party:
                            party = Party(id=party_id, name=winner["party"], abbreviation=None)
                            db.add(party)
                        person = db.get(Person, person_id)
                        if not person:
                            person = Person(id=person_id, full_name=name, identity_notes="2024 Lok Sabha election winner; name as listed by ADR/MyNeta.")
                            db.add(person)
                        else:
                            person.full_name = name
                        db.flush()
                        cons = db.get(Constituency, constituency_id)
                        if not cons:
                            cons = Constituency(id=constituency_id, name=constituency, state_name=state,
                                legislature="lok_sabha", geometry_source_url=WINNERS_URL, is_active=True)
                            db.add(cons)
                        candidacy_id = f"myneta-ls2024-candidacy-{pid}"
                        cand = db.get(Candidacy, candidacy_id)
                        if not cand:
                            cand = Candidacy(id=candidacy_id, person_id=person_id, constituency_id=constituency_id,
                                party_id=party_id, election_date=SNAPSHOT_DATE, status="elected",
                                source_document_id=source_id, valid_from=SNAPSHOT_DATE, valid_to=None,
                                verification_status=status, verification_notes=notes)
                            db.add(cand)
                        else:
                            cand.person_id=person_id; cand.constituency_id=constituency_id; cand.party_id=party_id
                            cand.election_date=SNAPSHOT_DATE; cand.status="elected"; cand.source_document_id=source_id
                            cand.valid_from=SNAPSHOT_DATE; cand.verification_status=status; cand.verification_notes=notes
                        db.flush()
                        for n, item in enumerate(rows, start=1):
                            case_id = f"myneta-ls2024-case-{pid}-{slug(item['section'])}-{n}"
                            case = db.get(CaseRecord, case_id)
                            case_title = f"{item['section']} as disclosed — {item['case_no'] or item['fir'] or ('case row ' + str(n))}"
                            statutory = "; ".join(x for x in [item["provisions"], item["other_acts"]] if x) or None
                            if not case:
                                case = CaseRecord(id=case_id, case_title=case_title, case_number=item["case_no"] or item["fir"] or None,
                                    court_name=item["court"] or None, offence_summary=item["summary"], statutory_provisions=statutory,
                                    is_serious=False, seriousness_rank=None,
                                    seriousness_basis="Not classified; no automatic offence-severity inference applied.",
                                    source_document_id=source_id, source_url=profile_url, declared_in_affidavit=True,
                                    filed_date=None, verification_status="verified")
                                db.add(case)
                            else:
                                case.case_title=case_title; case.case_number=item["case_no"] or item["fir"] or None
                                case.court_name=item["court"] or None; case.offence_summary=item["summary"]
                                case.statutory_provisions=statutory; case.source_document_id=source_id
                                case.source_url=profile_url; case.declared_in_affidavit=True; case.verification_status="verified"
                                case.seriousness_basis="Not classified; no automatic offence-severity inference applied."
                            link_id = f"{case_id}:{person_id}"
                            link = db.scalar(select(CasePersonLink).where(CasePersonLink.case_id==case_id, CasePersonLink.person_id==person_id))
                            if not link:
                                link = CasePersonLink(id=link_id, case_id=case_id, person_id=person_id, role="accused", identity_verification="verified")
                                db.add(link)
                            else:
                                link.identity_verification="verified"
                        db.commit()
                        imported += 1
                        case_rows += len(rows)
                    except Exception:
                        db.rollback()
                        raise
                    finally:
                        db.close()
                except Exception as exc:
                    review += 1
                    log.exception("Failed importing MyNeta profile %s: %s", profile_url, exc)
                STATUS.update(candidates_imported=imported, case_rows_imported=case_rows, needs_review=review)
                if idx % 25 == 0:
                    log.info("MyNeta 2024 import progress: %s/%s profiles; %s case rows; %s review flags",
                             idx, len(winners), case_rows, review)
                time.sleep(0.2)
        if imported < 450:
            raise RuntimeError(f"Only {imported} source-linked profiles imported successfully; completion marker withheld for safe retry.")
        db = SessionLocal()
        try:
            marker = SourceDocument(id="bootstrap-myneta-ls2024-complete",
                title="ADR/MyNeta Lok Sabha 2024 winners baseline import",
                source_type="dataset_import_run", source_url=WINNERS_URL, published_date=None,
                verification_status="verified", reviewer="automated-source-match",
                review_notes=f"Imported {imported} source-linked winner profiles from the ADR/MyNeta 2024 list (the list reports 543 winners; coverage is incomplete where individual profiles were unavailable). Parsed {case_rows} declared-case rows. {review} profile(s) need review because counts failed to match or fetches failed. Source-match does not mean independent court verification.")
            db.add(marker)
            db.commit()
        finally:
            db.close()
        STATUS.update(state="complete", finished_at=date.today().isoformat())
        log.info("MyNeta 2024 import complete: %s candidates, %s case rows, %s review flags", imported, case_rows, review)
    except Exception as exc:
        STATUS.update(state="error", finished_at=date.today().isoformat(), error=str(exc))
        log.exception("MyNeta 2024 import failed: %s", exc)
