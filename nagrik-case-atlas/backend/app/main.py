import os, uuid
from urllib.parse import urlparse
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_, or_, func
from pathlib import Path
from .db import Base, engine, get_db
from .models import Constituency, Person, Party, Candidacy, CaseRecord, CasePersonLink, CaseEvent, SourceDocument, SourceCheck, BoundaryVersion

Base.metadata.create_all(bind=engine)
app=FastAPI(title="India Constituency Explorer API", version="0.2.0", description="Source-linked public-record explorer. No candidate record should be published before verification.")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS","*").split(","), allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["Authorization","Content-Type"])
ADMIN_TOKEN=os.getenv("ADMIN_TOKEN", "")
ALLOWED_SOURCE_HOSTS={x.strip().lower() for x in os.getenv("ALLOWED_SOURCE_HOSTS","eci.gov.in,affidavit.eci.gov.in,services.ecourts.gov.in,hcservices.ecourts.gov.in,ecourts.gov.in,sci.gov.in,main.sci.gov.in").split(",") if x.strip()}
def source_url_allowed(url: str) -> bool:
    try:
        parsed=urlparse(url); host=(parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme=="https" and any(host==h or host.endswith("."+h) for h in ALLOWED_SOURCE_HOSTS)
    except Exception:
        return False
WEB_DIR=Path(os.getenv("WEB_DIR", str(Path(__file__).resolve().parents[2]/"web")))

@app.get("/api/health")
def health(db: Session=Depends(get_db)):
    try:
        db.execute(select(1))
        return {"status":"ok","database":"ok","mode":"source-linked records only","timestamp":datetime.now(timezone.utc).isoformat(),"live_monitoring":"not configured until sources and review process are configured"}
    except Exception:
        return {"status":"degraded","database":"error","mode":"records unavailable","detail":"Database unavailable; check server logs."}

@app.get("/api/coverage")
def coverage(db: Session=Depends(get_db)):
    return {
      "constituencies": db.scalar(select(func.count()).select_from(Constituency)) or 0,
      "verified_candidates": db.scalar(select(func.count()).select_from(Candidacy).where(Candidacy.verification_status=="verified")) or 0,
      "verified_cases": db.scalar(select(func.count()).select_from(CaseRecord).where(CaseRecord.verification_status=="verified")) or 0,
      "verified_events": db.scalar(select(func.count()).select_from(CaseEvent).where(CaseEvent.verification_status=="verified")) or 0,
      "review_queue": db.scalar(select(func.count()).select_from(CaseEvent).where(CaseEvent.verification_status.in_(["discovered","needs_review"]))) or 0,
      "last_verified_event": db.scalar(select(func.max(CaseEvent.verified_at)).where(CaseEvent.verification_status=="verified"))
    }

@app.get("/api/candidates")
def candidates(legislature: str="lok_sabha", constituency_name: str="", state: str="", as_of: date=date.today(), history_mode: str="known", sort: str="cases", db: Session=Depends(get_db)):
    if history_mode not in ("known","corrected"):
        raise HTTPException(400,"history_mode must be known or corrected")
    q=select(Candidacy).join(Candidacy.person).join(Candidacy.constituency).options(joinedload(Candidacy.person),joinedload(Candidacy.party),joinedload(Candidacy.constituency)).where(Constituency.legislature==legislature, Constituency.name.ilike(constituency_name), Constituency.state_name.ilike(state), Candidacy.verification_status=="verified", Candidacy.source_document_id.in_(select(SourceDocument.id).where(SourceDocument.verification_status=="verified")), Candidacy.valid_from<=as_of, or_(Candidacy.valid_to.is_(None),Candidacy.valid_to>=as_of))
    rows=db.scalars(q).all(); items=[]
    # Show the latest candidate roster known for the selected constituency at this date.
    eligible=[c for c in rows if c.election_date and c.election_date<=as_of]
    if eligible:
        latest_election=max(c.election_date for c in eligible)
        rows=[c for c in eligible if c.election_date==latest_election]
    else:
        rows=[]
    for cand in rows:
        links=db.scalars(select(CasePersonLink).join(CaseRecord).where(CasePersonLink.person_id==cand.person_id, CasePersonLink.identity_verification=="verified", CaseRecord.verification_status=="verified", CaseRecord.source_document_id.in_(select(SourceDocument.id).where(SourceDocument.verification_status=="verified")))).all()
        cases=[]
        for link in links:
            case=db.get(CaseRecord,link.case_id)
            if history_mode=="known" and case.created_at and case.created_at.date()>as_of: continue
            if history_mode=="corrected" and not case.filed_date: continue
            evq=select(CaseEvent).where(CaseEvent.case_id==case.id, CaseEvent.verification_status=="verified")
            evq=evq.where(CaseEvent.source_document_id.in_(select(SourceDocument.id).where(SourceDocument.verification_status=="verified")))
            if history_mode=="known": evq=evq.where(CaseEvent.recorded_at<=datetime.combine(as_of,datetime.max.time(),timezone.utc))
            else: evq=evq.where(CaseEvent.event_date<=as_of)
            evs=db.scalars(evq.order_by(CaseEvent.event_date.desc(),CaseEvent.recorded_at.desc())).all()
            status=evs[0].status_after_event if evs and evs[0].status_after_event else "Status not recorded"
            if not evs and case.filed_date and case.filed_date>as_of: continue
            if case.filed_date and case.filed_date>as_of: continue
            cases.append({"id":case.id,"case_title":case.case_title,"case_number":case.case_number,"court_name":case.court_name,"description":case.offence_summary,"statutory_provisions":case.statutory_provisions,"is_serious":case.is_serious,"seriousness_rank":case.seriousness_rank,"declared_in_affidavit":case.declared_in_affidavit,"current_status":status,"source_url":case.source_url,"last_verified_at":evs[0].verified_at.isoformat() if evs and evs[0].verified_at else None,"event_history":[{"event_date":e.event_date.isoformat(),"type":e.event_type,"summary":e.summary,"status":e.status_after_event,"source_document_id":e.source_document_id} for e in reversed(evs)]})
        serious=[c for c in cases if c["is_serious"]]
        ranked=[c for c in cases if c.get("seriousness_rank") is not None]
        most=sorted(ranked,key=lambda c:(c["seriousness_rank"],c["case_title"]))
        items.append({"candidate_id":cand.person_id,"name":cand.person.full_name,"party_name":cand.party.name if cand.party else "Independent / not recorded","candidacy_status":cand.status,"verification_status":cand.verification_status,"verified_case_count":len({c['id'] for c in cases}),"declared_case_count":len({c['id'] for c in cases if c.get('declared_in_affidavit')}),"serious_case_count":len({c['id'] for c in serious}),"most_serious_case":{"description":most[0]["description"],"status":most[0]["current_status"],"court_name":most[0]["court_name"],"source_url":most[0]["source_url"]} if most else None,"cases":cases})
    if sort=="name": items.sort(key=lambda x:x["name"].casefold())
    elif sort=="serious": items.sort(key=lambda x:(x["serious_case_count"],x["verified_case_count"],x["name"].casefold()))
    else: items.sort(key=lambda x:(x["verified_case_count"],x["name"].casefold()))
    return {"items":items,"as_of":as_of.isoformat(),"history_mode":history_mode,"count":len(items),"note":"Only verified records are returned. Empty results mean no verified records are loaded for this selection, not that no cases exist."}

@app.get("/api/constituencies")
def constituencies(legislature: Optional[str]=None, state: Optional[str]=None, q: Optional[str]=None, db: Session=Depends(get_db)):
    stmt=select(Constituency).where(Constituency.is_active==True)
    if legislature: stmt=stmt.where(Constituency.legislature==legislature)
    if state: stmt=stmt.where(Constituency.state_name.ilike(f"%{state}%"))
    if q: stmt=stmt.where(Constituency.name.ilike(f"%{q}%"))
    rows=db.scalars(stmt.order_by(Constituency.state_name,Constituency.name).limit(500)).all()
    return {"items":[{"id":r.id,"name":r.name,"state":r.state_name,"legislature":r.legislature,"boundary_version_id":r.boundary_version_id} for r in rows],"count":len(rows)}

@app.get("/api/changes")
def changes(since: Optional[datetime]=None, limit: int=50, db: Session=Depends(get_db)):
    limit=max(1,min(limit,200)); stmt=select(CaseEvent).where(CaseEvent.verification_status=="verified")
    if since: stmt=stmt.where(CaseEvent.recorded_at>since)
    rows=db.scalars(stmt.order_by(CaseEvent.recorded_at.desc()).limit(limit)).all()
    return {"items":[{"id":e.id,"case_id":e.case_id,"event_type":e.event_type,"event_date":e.event_date.isoformat(),"recorded_at":e.recorded_at.isoformat(),"summary":e.summary,"status_after_event":e.status_after_event,"source_document_id":e.source_document_id} for e in rows]}

@app.get("/api/sources")
def sources(db: Session=Depends(get_db)):
    rows=db.scalars(select(SourceDocument).where(SourceDocument.verification_status=="verified").order_by(SourceDocument.retrieved_at.desc()).limit(200)).all()
    return {"items":[{"id":s.id,"title":s.title,"type":s.source_type,"url":s.source_url,"published_date":s.published_date.isoformat() if s.published_date else None,"retrieved_at":s.retrieved_at.isoformat(),"verification_status":s.verification_status,"reviewer":s.reviewer,"review_notes":s.review_notes} for s in rows]}

def require_admin(authorization: str|None):
    if not ADMIN_TOKEN:
        raise HTTPException(503,"Admin import is disabled: set ADMIN_TOKEN in the environment first")
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(401,"Invalid admin token")

@app.post("/api/admin/source-documents")
def add_source_document(payload: dict, authorization: str|None=Header(default=None), db: Session=Depends(get_db)):
    require_admin(authorization)
    required=["title","source_type","source_url"]
    if any(not payload.get(k) for k in required): raise HTTPException(400,f"Required fields: {', '.join(required)}")
    if not source_url_allowed(payload["source_url"]): raise HTTPException(400,"Source URL must be HTTPS and use an allowlisted official source host")
    row=SourceDocument(id=payload.get("id") or str(uuid.uuid4()),title=payload["title"],source_type=payload["source_type"],source_url=payload["source_url"],published_date=date.fromisoformat(payload["published_date"]) if payload.get("published_date") else None,verification_status="discovered",review_notes="Added to source register; not yet verified.")
    db.add(row); db.commit(); return {"id":row.id,"status":"discovered","message":"Source registered for review; no legal conclusion has been inferred."}

@app.post("/api/admin/review-event/{event_id}")
def review_event(event_id: str, payload: dict, authorization: str|None=Header(default=None), db: Session=Depends(get_db)):
    require_admin(authorization)
    ev=db.get(CaseEvent,event_id)
    if not ev: raise HTTPException(404,"Event not found")
    decision=payload.get("decision")
    if decision not in ("verified","rejected","needs_review"): raise HTTPException(400,"decision must be verified, rejected, or needs_review")
    if decision=="verified" and not payload.get("reviewer"): raise HTTPException(400,"A reviewer identifier is required")
    if decision=="verified":
        if not ev.source_document_id: raise HTTPException(400,"A verified source document is required before this event can be verified")
        source=db.get(SourceDocument,ev.source_document_id)
        if not source or source.verification_status!="verified": raise HTTPException(400,"Verify the linked source document before verifying this event")
    ev.verification_status=decision; ev.verified_by=payload.get("reviewer"); ev.verified_at=datetime.now(timezone.utc) if decision=="verified" else None
    db.commit(); return {"id":ev.id,"verification_status":ev.verification_status,"verified_at":ev.verified_at.isoformat() if ev.verified_at else None}


@app.post("/api/admin/review-source/{source_id}")
def review_source(source_id: str, payload: dict, authorization: str|None=Header(default=None), db: Session=Depends(get_db)):
    require_admin(authorization)
    source=db.get(SourceDocument,source_id)
    if not source: raise HTTPException(404,"Source document not found")
    decision=payload.get("decision")
    if decision not in ("verified","rejected","needs_review"): raise HTTPException(400,"decision must be verified, rejected, or needs_review")
    if decision=="verified" and not payload.get("reviewer"): raise HTTPException(400,"A reviewer identifier is required")
    source.verification_status=decision; source.reviewer=payload.get("reviewer"); source.review_notes=payload.get("notes",source.review_notes)
    db.commit(); return {"id":source.id,"verification_status":source.verification_status,"reviewer":source.reviewer}

@app.get("/api/admin/queue")
def review_queue(authorization: str|None=Header(default=None), db: Session=Depends(get_db)):
    require_admin(authorization)
    docs=db.scalars(select(SourceDocument).where(SourceDocument.verification_status.in_(["discovered","needs_review"])).order_by(SourceDocument.retrieved_at.desc()).limit(200)).all()
    events=db.scalars(select(CaseEvent).where(CaseEvent.verification_status.in_(["discovered","needs_review"])).order_by(CaseEvent.recorded_at.desc()).limit(200)).all()
    return {"documents":[{"id":d.id,"title":d.title,"url":d.source_url,"status":d.verification_status} for d in docs],"events":[{"id":e.id,"case_id":e.case_id,"summary":e.summary,"event_date":e.event_date.isoformat(),"status":e.verification_status} for e in events]}

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIR/"index.html")
@app.get("/admin", include_in_schema=False)
def admin_home():
    return FileResponse(WEB_DIR/"admin.html")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
