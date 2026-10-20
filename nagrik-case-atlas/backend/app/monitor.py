"""Periodic integrity monitor for registered individual source documents.
It detects changes only; it never converts a changed document into a legal conclusion.
"""
import hashlib, os, time, uuid, ipaddress, socket
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import SourceDocument, SourceCheck
Base.metadata.create_all(bind=engine)
DEFAULT_ALLOWED={"eci.gov.in","affidavit.eci.gov.in","services.ecourts.gov.in","hcservices.ecourts.gov.in","ecourts.gov.in","sci.gov.in","main.sci.gov.in"}
ALLOWED=set(x.strip().lower() for x in os.getenv('ALLOWED_SOURCE_HOSTS',','.join(DEFAULT_ALLOWED)).split(',') if x.strip())

def host_allowed(host):
    host=(host or '').lower().rstrip('.')
    return any((host.endswith(x[1:]) if x.startswith('*.') else (host==x or host.endswith('.'+x))) for x in ALLOWED)

def check_url(url):
    p=urlparse(url)
    if p.scheme!='https' or not host_allowed(p.hostname): raise ValueError('URL must be HTTPS and its hostname must be allowlisted in ALLOWED_SOURCE_HOSTS')
    try:
        for item in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
            ip=ipaddress.ip_address(item[4][0])
            if not ip.is_global: raise ValueError('Private or non-public source host is blocked')
    except socket.gaierror: raise ValueError('Source hostname could not be resolved')

def run_once():
    db=SessionLocal(); results=[]
    try:
        docs=db.scalars(select(SourceDocument).where(SourceDocument.verification_status!='rejected')).all()
        for doc in docs:
            checked=datetime.now(timezone.utc); status=None; digest=None; changed=False; note=''
            try:
                check_url(doc.source_url)
                with httpx.Client(timeout=20,follow_redirects=False,headers={'User-Agent':'IndiaConstituencyExplorer-source-monitor/0.1 (public-record integrity check)'}) as client:
                    response=client.get(doc.source_url)
                status=response.status_code
                if status in (301,302,303,307,308): note='Redirect not followed; verify the destination and register the canonical source URL.'
                elif status>=400: note=f'HTTP {status}; source needs manual attention.'
                else:
                    body=response.content[:10_000_000]
                    digest=hashlib.sha256(body).hexdigest()
                    changed=bool(doc.content_sha256 and doc.content_sha256!=digest)
                    if changed:
                        doc.verification_status='needs_review'
                        doc.review_notes=(doc.review_notes or '')+'\nSource content hash changed; review the new source before changing any case status.'
                        note='Content changed; queued for human review. No automatic legal status update.'
                    elif not doc.content_sha256:
                        note='First content hash recorded. Human review is still required.'
                    else: note='No content-hash change detected.'
                    doc.content_sha256=digest; doc.retrieved_at=checked
            except Exception as e: note=str(e)
            db.add(SourceCheck(id=str(uuid.uuid4()),source_document_id=doc.id,checked_at=checked,http_status=status,observed_sha256=digest,changed=changed,note=note))
            results.append({'source_id':doc.id,'status':status,'changed':changed,'note':note})
        db.commit(); return results
    finally: db.close()

if __name__=='__main__':
    interval=max(1,int(os.getenv('MONITOR_INTERVAL_HOURS','6')))*3600
    while True:
        try:
            for result in run_once(): print(result,flush=True)
        except Exception as exc: print({'monitor_error':str(exc)},flush=True)
        time.sleep(interval)
