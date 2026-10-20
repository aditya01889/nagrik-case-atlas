"""Import normalized, reviewed CSVs. Empty templates are provided; no sample political claims are seeded."""
import csv, os, sys, uuid
from pathlib import Path
from datetime import date, datetime, timezone
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import Constituency, Person, Party, Candidacy, CaseRecord, CasePersonLink, CaseEvent, SourceDocument, BoundaryVersion

Base.metadata.create_all(bind=engine)

def rows(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def val(row,key,default=None):
    x=row.get(key,'')
    return x.strip() if isinstance(x,str) and x.strip() else default
def dt(s): return date.fromisoformat(s) if s else None

def import_dir(folder):
    folder=Path(folder); db=SessionLocal(); counts={}
    try:
        for r in rows(folder/'constituencies.csv'):
            rid=val(r,'id') or f"{val(r,'legislature')}:{val(r,'state_name')}:{val(r,'name')}"
            obj=db.get(Constituency,rid) or Constituency(id=rid,name=val(r,'name'),state_name=val(r,'state_name'),legislature=val(r,'legislature'),boundary_version_id=val(r,'boundary_version_id'),geometry_source_url=val(r,'geometry_source_url'),is_active=(val(r,'is_active','true').lower()=='true'))
            obj.name=val(r,'name'); obj.state_name=val(r,'state_name'); obj.legislature=val(r,'legislature'); obj.boundary_version_id=val(r,'boundary_version_id'); obj.geometry_source_url=val(r,'geometry_source_url'); obj.is_active=val(r,'is_active','true').lower()=='true'; db.add(obj)
        db.flush(); counts['constituencies']=len(rows(folder/'constituencies.csv'))
        for r in rows(folder/'parties.csv'):
            rid=val(r,'id') or val(r,'name').lower().replace(' ','-')
            obj=db.get(Party,rid) or Party(id=rid,name=val(r,'name'),abbreviation=val(r,'abbreviation'))
            obj.name=val(r,'name'); obj.abbreviation=val(r,'abbreviation'); db.add(obj)
        db.flush(); counts['parties']=len(rows(folder/'parties.csv'))
        for r in rows(folder/'people.csv'):
            rid=val(r,'id') or str(uuid.uuid4())
            obj=db.get(Person,rid) or Person(id=rid,full_name=val(r,'full_name'))
            obj.full_name=val(r,'full_name'); obj.identity_notes=val(r,'identity_notes'); db.add(obj)
        db.flush(); counts['people']=len(rows(folder/'people.csv'))
        for r in rows(folder/'source_documents.csv'):
            rid=val(r,'id') or str(uuid.uuid4())
            obj=db.get(SourceDocument,rid) or SourceDocument(id=rid,title=val(r,'title'),source_type=val(r,'source_type'),source_url=val(r,'source_url'))
            obj.title=val(r,'title'); obj.source_type=val(r,'source_type'); obj.source_url=val(r,'source_url'); obj.published_date=dt(val(r,'published_date')); obj.content_sha256=val(r,'content_sha256'); obj.verification_status=val(r,'verification_status','discovered'); obj.reviewer=val(r,'reviewer'); obj.review_notes=val(r,'review_notes'); db.add(obj)
        db.flush(); counts['source_documents']=len(rows(folder/'source_documents.csv'))
        for r in rows(folder/'candidacies.csv'):
            rid=val(r,'id') or str(uuid.uuid4())
            obj=db.get(Candidacy,rid) or Candidacy(id=rid,person_id=val(r,'person_id'),constituency_id=val(r,'constituency_id'),election_date=dt(val(r,'election_date')),valid_from=dt(val(r,'valid_from')))
            obj.person_id=val(r,'person_id'); obj.constituency_id=val(r,'constituency_id'); obj.party_id=val(r,'party_id'); obj.election_date=dt(val(r,'election_date')); obj.status=val(r,'status','contesting'); obj.source_document_id=val(r,'source_document_id'); obj.valid_from=dt(val(r,'valid_from')) or dt(val(r,'election_date')); obj.valid_to=dt(val(r,'valid_to')); obj.verification_status=val(r,'verification_status','discovered'); obj.verification_notes=val(r,'verification_notes'); db.add(obj)
        db.flush(); counts['candidacies']=len(rows(folder/'candidacies.csv'))
        for r in rows(folder/'cases.csv'):
            rid=val(r,'id') or str(uuid.uuid4())
            obj=db.get(CaseRecord,rid) or CaseRecord(id=rid,case_title=val(r,'case_title'),offence_summary=val(r,'offence_summary'))
            obj.case_title=val(r,'case_title'); obj.case_number=val(r,'case_number'); obj.court_name=val(r,'court_name'); obj.offence_summary=val(r,'offence_summary'); obj.statutory_provisions=val(r,'statutory_provisions'); obj.is_serious=val(r,'is_serious','false').lower()=='true'; obj.seriousness_rank=int(val(r,'seriousness_rank')) if val(r,'seriousness_rank') else None; obj.seriousness_basis=val(r,'seriousness_basis'); obj.source_document_id=val(r,'source_document_id'); obj.source_url=val(r,'source_url'); obj.declared_in_affidavit=val(r,'declared_in_affidavit','false').lower()=='true'; obj.filed_date=dt(val(r,'filed_date')); obj.verification_status=val(r,'verification_status','discovered'); db.add(obj)
            person_id=val(r,'person_id')
            if person_id:
                link_id=f"{rid}:{person_id}"
                link=db.scalar(select(CasePersonLink).where(CasePersonLink.case_id==rid,CasePersonLink.person_id==person_id))
                if not link: link=CasePersonLink(id=link_id,case_id=rid,person_id=person_id,role=val(r,'role','accused'),identity_verification=val(r,'identity_verification','unverified'))
                else: link.role=val(r,'role','accused'); link.identity_verification=val(r,'identity_verification','unverified')
                db.add(link)
        db.flush(); counts['cases']=len(rows(folder/'cases.csv'))
        for r in rows(folder/'case_events.csv'):
            rid=val(r,'id') or str(uuid.uuid4())
            obj=db.get(CaseEvent,rid) or CaseEvent(id=rid,case_id=val(r,'case_id'),event_type=val(r,'event_type'),event_date=dt(val(r,'event_date')),summary=val(r,'summary'))
            obj.case_id=val(r,'case_id'); obj.event_type=val(r,'event_type'); obj.event_date=dt(val(r,'event_date')); obj.status_after_event=val(r,'status_after_event'); obj.summary=val(r,'summary'); obj.source_document_id=val(r,'source_document_id'); obj.verification_status=val(r,'verification_status','discovered'); obj.verified_by=val(r,'verified_by'); obj.verified_at=datetime.fromisoformat(val(r,'verified_at')) if val(r,'verified_at') else None; db.add(obj)
        db.flush(); counts['case_events']=len(rows(folder/'case_events.csv'))
        db.commit(); return counts
    except Exception:
        db.rollback(); raise
    finally: db.close()

if __name__=='__main__':
    folder=sys.argv[1] if len(sys.argv)>1 else 'data/import_templates'
    print(import_dir(folder))
