from pathlib import Path
import tempfile,tarfile,json,subprocess,hashlib,ast
REPO=Path('/workspace/nana-core')
meta=json.loads((REPO/'docs/nana_r042_evidence/package-build-delivery.json').read_text())
archive=REPO/'.nana-experiment/r042'/meta['filename']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['SHA256']
with tempfile.TemporaryDirectory(prefix='nana-r042-package-check-') as td:
    temp=Path(td)
    with tarfile.open(archive) as tar:tar.extractall(temp,filter='data')
    root=temp/'nana-r042-empty-c6eb725'
    m=json.loads((root/'manifest.json').read_text())
    assert m['production_review_pins']==m['real_runtime_proof_pins']==0 and m['seal_mode']=='EMPTY'
    expected=m['files']
    for f,h in expected.items():assert hashlib.sha256((root/f).read_bytes()).hexdigest()==h
    bm=json.loads((root/'package/bundle_manifest.json').read_text())
    assert len(bm['core_files'])==55 and bm['source_commit']=='ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513'
    for n,h in bm['core_files'].items():assert hashlib.sha256((root/'package'/n).read_bytes()).hexdigest()==h
    assert not any(p.suffix in ('.db','.sqlite','.pyc') or p.name.endswith(('-wal','-shm')) for p in root.rglob('*'))
    events=[]
    def run(script,*args,ok=True):
        out=subprocess.run([str(root/script),*map(str,args)],capture_output=True,text=True,cwd=root)
        assert out.returncode==(0 if ok else 2),(script,args,out.returncode,out.stdout,out.stderr)
        assert not out.stderr,out.stderr
        d=json.loads(out.stdout)
        events.append({'operation':script+' '+str(args[0]),'returncode':out.returncode,'status':d.get('status',d.get('state','UNKNOWN'))})
        return d
    directory=temp/'shadow';directory.mkdir(mode=0o700)
    init=run('r04.sh','receipt','init','--directory',directory)
    scope=temp/'scope.json';scope.write_text(json.dumps({'platform_scope':'aiocqhttp','event_type_scope':'GroupMessage','sender_hash':'b'*64,'conversation_hash':'c'*64}))
    raw_ids=temp/'authorized-id-metadata.json'
    raw_ids.write_text(json.dumps({'platform_scope':'aiocqhttp','event_type_scope':'GroupMessage','sender_id':'synthetic-sender','conversation_id':'synthetic-conversation'}))
    hashed_scope=temp/'hashed-scope.json'
    hashed=run('onboarding.sh','scope','--directory',directory,'--input',raw_ids,'--output',hashed_scope)
    assert hashed['raw_identifiers_exported'] is False
    assert 'synthetic-sender' not in hashed_scope.read_text() and 'synthetic-conversation' not in hashed_scope.read_text()
    scope=hashed_scope
    request=temp/'request'
    prep=run('onboarding.sh','prepare','--directory',directory,'--scope',scope,'--output',request)
    assert prep['store_binding']==init['store_binding'] and prep['production_authority_created'] is False
    rid=prep['receipt_id']
    run('r04.sh','receipt','create','--directory',directory,'--input',request/'receipt.json')
    run('r04.sh','receipt','review','--directory',directory,'--receipt-id',rid,'--input',request/'review.json',ok=False)
    run('r04.sh','receipt','arm','--directory',directory,'--receipt-id',rid,ok=False)
    run('r04.sh','receipt','arm','--directory',directory,'--receipt-id',rid,'--force',ok=False)
    state=run('r04.sh','receipt','status','--directory',directory,'--receipt-id',rid)
    assert state['state']=='CREATED' and state['uses']==0
    other=temp/'other-shadow';other.mkdir(mode=0o700);run('r04.sh','receipt','init','--directory',other)
    run('r04.sh','receipt','create','--directory',other,'--input',request/'receipt.json',ok=False)
    run('r04.sh','receipt','disarm','--directory',directory,'--receipt-id',rid)
    run('r04.sh','receipt','arm','--directory',directory,'--receipt-id',rid,ok=False)
    # Source-pinned file isolation + fixture promotion rejection exercised in delivered entrypoint.
    fixture_repo=temp/'fixture-review';fixture_repo.mkdir()
    def git(*args):return subprocess.check_output(['git',*args],cwd=fixture_repo,stderr=subprocess.DEVNULL).decode().strip()
    git('init');p=fixture_repo/'reviews/r042/fixture.json';p.parent.mkdir(parents=True)
    r=json.loads((request/'receipt.json').read_text());r['review_provenance']='FIXTURE'
    auth={k:v for k,v in r.items() if k!='review_receipt_digest'}
    def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    doc={'schema_version':1,'receipt_id':r['receipt_id'],'store_binding':r['store_binding'],'review_provenance':'FIXTURE','authorization_digest':digest(auth)}
    r['review_receipt_digest']=digest(doc)
    review={'schema_version':1,'kind':'AUTHORIZATION_REVIEW','reviewer_origin':'NANA_INDEPENDENT_HOST_REVIEW',
           'operator_authorization_digest':digest(auth),'host_metadata_evidence_digest':'d'*64,
           'confirmation':'INDEPENDENTLY_REVIEWED_EXACT_ONE_SHOT',
           'receipt':json.dumps(r,sort_keys=True,separators=(',',':')),'review':doc,'runtime_report':None}
    p.write_text(json.dumps(review,sort_keys=True,separators=(',',':')))
    git('add','.');git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-m','Synthetic fixture review, not host evidence')
    sha=git('rev-parse','HEAD');out=temp/'must-not-build'
    run('onboarding.sh','seal','--base',root,'--output',out,'--review-repo',fixture_repo,'--review-sha',sha,'--review-path','reviews/r042/fixture.json',ok=False)
    assert not out.exists()
    # Old fixture harness still proves engineered ingress/barrier only, no real upgrades.
    harness=run('r04.sh','harness')
    assert harness['host_binding']=='UNVERIFIED'
    # Tampered source cannot be loaded before integrity guard.
    seal=root/'package/support/tools/nana_astrbot_shadow/sealed_trust.py'
    seal.write_text(seal.read_text()+'\nSEAL_MODE="ONE_SHOT"\n')
    run('r04.sh','receipt','status','--directory',directory,'--receipt-id',rid,ok=False)
    report={'origin':'DEVELOPMENT_EXTRACTED_EMPTY_PACKAGE','status':'PASS','Core55_byte_hashes':'PASS',
        'archive':meta,'operations':events,'production_pins':0,'real_runtime_pins':0,
        'fixture_promotion':'BLOCKED','copied_receipt':'BLOCKED','untrusted_arm':'BLOCKED',
        'tampered_package':'BLOCKED','real_host_actions':0,'real_authorizations_created':0,'host_binding':'UNVERIFIED'}
    (REPO/'docs/nana_r042_evidence/package-validation.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'package_validation':'PASS','operations':len(events),'core55':'PASS','actual_production_pins':0}))
