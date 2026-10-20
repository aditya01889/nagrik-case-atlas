"""Download a public GeoJSON boundary file and register its features as unverified geometry metadata.
This does not certify boundary legality. Validate the source before publishing.
"""
import argparse, hashlib, json, re, urllib.request
from datetime import date
from pathlib import Path
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import Constituency, BoundaryVersion
Base.metadata.create_all(bind=engine)

def slug(s):
    return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',str(s).lower())).strip('-')
def find_prop(props, patterns):
    for pat in patterns:
        for k,v in props.items():
            if re.fullmatch(pat,k,re.I) and v not in (None,''): return str(v)
    for k,v in props.items():
        if any(re.search(p,k,re.I) for p in patterns) and v not in (None,''): return str(v)
    return None

def sync(url, legislature, expected, effective_from, license_name, output=None):
    req=urllib.request.Request(url,headers={'User-Agent':'IndiaConstituencyExplorer-boundary-import/0.1'})
    with urllib.request.urlopen(req,timeout=45) as resp: raw=resp.read(100_000_000)
    data=json.loads(raw); features=data.get('features',[])
    if expected and len(features)!=expected: raise ValueError(f'Expected {expected} features; received {len(features)}. No records imported.')
    if not features: raise ValueError('GeoJSON has no features.')
    parsed=[]
    for i,f in enumerate(features):
        props=f.get('properties') or {}; geom=f.get('geometry') or {}
        name=find_prop(props,[r'(pc_name|pcname|constituency_name|constituency|name|ac_name|acname|seat_name)'])
        state=find_prop(props,[r'(state_name|state|st_name|st_nm|state_nm)']) or 'Unknown state'
        if not name or geom.get('type') not in ('Polygon','MultiPolygon'): continue
        parsed.append((name,state))
    if len(parsed)<expected*0.9 if expected else len(parsed)<len(features)*0.9: raise ValueError(f'Only {len(parsed)} named polygon features passed basic validation; aborting.')
    digest=hashlib.sha256(raw).hexdigest()
    version_id=f"{legislature}:{effective_from}:{digest[:12]}"
    db=SessionLocal()
    try:
        bv=db.get(BoundaryVersion,version_id)
        if not bv:
            bv=BoundaryVersion(id=version_id,legislature=legislature,source_url=url,source_license=license_name,effective_from=effective_from,sha256=digest,validation_status='unverified',validation_notes='Basic GeoJSON structure checked only. Must be reconciled against official delimitation orders before production use.')
            db.add(bv)
        created=0
        for name,state in parsed:
            cid=f"{legislature}:{slug(state)}:{slug(name)}"
            row=db.get(Constituency,cid)
            if not row:
                row=Constituency(id=cid,name=name,state_name=state,legislature=legislature,boundary_version_id=version_id,geometry_source_url=url,is_active=True); db.add(row); created+=1
            else:
                row.name=name; row.state_name=state; row.boundary_version_id=version_id; row.geometry_source_url=url; row.is_active=True
        db.commit()
        if output:
            Path(output).parent.mkdir(parents=True,exist_ok=True); Path(output).write_bytes(raw)
        return {'features':len(features),'named_polygon_features':len(parsed),'new_constituencies':created,'boundary_version_id':version_id,'sha256':digest,'validation_status':'unverified'}
    except Exception:
        db.rollback(); raise
    finally: db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True)
    p.add_argument('--legislature',choices=['lok_sabha','assembly'],required=True)
    p.add_argument('--expected-features',type=int,default=0)
    p.add_argument('--effective-from',type=date.fromisoformat,required=True)
    p.add_argument('--license',default='unknown — verify source licence')
    p.add_argument('--output',default=None,help='Optional path to save exact downloaded GeoJSON bytes')
    a=p.parse_args()
    print(json.dumps(sync(a.url,a.legislature,a.expected_features,a.effective_from,a.license,a.output),indent=2))
