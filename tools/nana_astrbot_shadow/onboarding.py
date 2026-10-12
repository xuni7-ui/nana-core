"""Offline build-time sealing. No runtime pin setter, host operation or fixture trust.

An authorized independent reviewer commits the exact metadata review to Git.
The builder reads that immutable blob; Git/hash proves bytes, not reviewer honesty.
Source review and operator approval are mandatory human trust-boundary operations.
"""
import argparse
from datetime import datetime, timedelta, timezone
import gzip
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
from uuid import uuid4
from tools.nana_host_shadow.safety import canonical, checked_path, digest, private_file, read_json, verify_bundle
from .one_shot import OneShotReceipt, Provenance, parse_receipt, review_document, utc
from .one_shot_cli import operator_ledger, _SafeParser
from .package import verify_package
from .one_shot_proof import REPORT_KEYS, ZERO_KEYS

HEX = re.compile(r'[0-9a-f]{64}\Z')
SCOPE_KEYS = {'platform_scope','conversation_hash','sender_hash','event_type_scope'}
REVIEW_KEYS = {'schema_version','kind','reviewer_origin','operator_authorization_digest',
              'host_metadata_evidence_digest','confirmation','receipt','review','runtime_report'}


def prepare(directory, scope, output, *, now=None):
    """Unsigned request, not a trusted review or an authority. No raw IDs accepted."""
    if type(scope) is not dict or set(scope)!=SCOPE_KEYS:raise ValueError('EXACT_HASHED_SCOPE_REQUIRED')
    with operator_ledger(directory) as l:
        binding=l.binding
        hash_scope=json.loads(l.store.one('core_meta','r04.hash_scope')['value_json'])
    now=now or datetime.now(timezone.utc)
    stamp=utc(now.isoformat())
    r=OneShotReceipt(receipt_id='r04-'+uuid4().hex,issued_at=stamp.isoformat(),
        expires_at=(stamp+timedelta(seconds=600)).isoformat(),store_binding=binding,hash_scope=hash_scope,
        review_provenance=Provenance.ASTRBOT_REAL_MESSAGE,review_receipt_digest='0'*64,**scope)
    review=review_document(r)
    r=parse_receipt(r.model_copy(update={'review_receipt_digest':digest(review)}).canonical())
    out=checked_path(output,directory=True,missing=True)
    if out.exists():raise ValueError('NEW_PREPARATION_DIRECTORY_REQUIRED')
    out.mkdir(mode=0o700)
    # Receipt parser deliberately requires canonical bytes WITHOUT trailing newline.
    (out/'receipt.json').write_text(r.canonical());(out/'receipt.json').chmod(0o600)
    private_file(out/'review.json',review)
    request={'status':'UNTRUSTED_REVIEW_REQUEST','receipt_digest':r.receipt_digest,
             'authorization_digest':r.authorization_digest,'review_receipt_digest':digest(review),
             'store_binding':binding,'receipt_id':r.receipt_id,'expires_at':r.expires_at,
             'production_authority_created':False}
    private_file(out/'request.json',request)
    return request


def make_review(preparation, approval, output, *, runtime_report=None):
    """Reviewer-side digest recomputation. Output is UNTRUSTED until source review."""
    p=checked_path(preparation,directory=True)
    file=checked_path(p/'receipt.json')
    if file.stat().st_size>4096:raise ValueError('RECEIPT_SIZE')
    r=parse_receipt(file.read_text())
    expected={'reviewer_origin','operator_authorization_digest','host_metadata_evidence_digest','confirmation'}
    if type(approval) is not dict or set(approval)!=expected:raise ValueError('APPROVAL_METADATA_ONLY')
    doc=review_document(r)
    if digest(doc)!=r.review_receipt_digest or read_json(p/'review.json')!=doc:raise ValueError('INDEPENDENT_DIGEST_MISMATCH')
    review={'schema_version':1,'kind':'RUNTIME_PROOF_REVIEW' if runtime_report is not None else 'AUTHORIZATION_REVIEW',
            **approval,'receipt':r.canonical(),'review':doc,'runtime_report':runtime_report}
    validate_review(review)
    private_file(output,review)
    return {'status':'UNTRUSTED_SOURCE_REVIEW_DOCUMENT','review_receipt_digest':digest(doc),
            'source_review_digest':digest(review),'receipt_digest':r.receipt_digest,
            'production_authority_created':False}


def source_review(repo, sha, path):
    """No working-tree/config/URL input. Pin reviewed bytes to an immutable commit."""
    repo=checked_path(repo,directory=True)
    if type(sha) is not str or not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('FULL_REVIEW_COMMIT_REQUIRED')
    if type(path) is not str or not re.fullmatch(r'reviews/r042/[a-z0-9_-]{1,80}\.json',path):
        raise ValueError('REVIEW_SOURCE_PATH')
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL)
    if git('rev-parse',sha+'^{commit}').decode().strip()!=sha:raise ValueError('REVIEW_COMMIT_REQUIRED')
    size=int(git('cat-file','-s',sha+':'+path))
    if size>65536:raise ValueError('REVIEW_SIZE')
    raw=git('show',sha+':'+path).decode('utf-8')
    d=json.loads(raw)
    if raw.rstrip('\n')!=canonical(d) or raw not in (canonical(d),canonical(d)+'\n'):
        raise ValueError('CANONICAL_REVIEW_SOURCE_REQUIRED')
    return d


def validate_core_metadata(core):
    """The source review archive must not become a raw-memory/body export."""
    keys={'identity_id','identity_revision','core_evidence_id','observation_id','goal_candidate_id',
          'shadow_plan_id','shadow_decision_id','dedup_result','barrier_result','event_timestamp',
          'metadata_hash','zero_execution_counts','model_semantics_verified'}
    if type(core) is not dict or set(core)!=keys:raise ValueError('CORE_METADATA_ONLY')
    for k in ('identity_id','core_evidence_id','observation_id'):
        if type(core[k]) is not str or not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',core[k]):
            raise ValueError('CORE_LINK_ID')
    for k in ('goal_candidate_id','metadata_hash'):
        if type(core[k]) is not str or not HEX.fullmatch(core[k]):raise ValueError('CORE_LINK_HASH')
    if (type(core['identity_revision']) is not int or core['identity_revision']<1
        or type(core['shadow_decision_id']) is not str or not re.fullmatch('cloud.shadow:[0-9a-f]{64}',core['shadow_decision_id'])
        or core['shadow_plan_id']!=core['shadow_decision_id']+'#plan_draft'
        or core['dedup_result'] not in ('NEW','DUPLICATE') or core['barrier_result']!='SHADOW_BLOCKED'
        or core['model_semantics_verified'] is not False):raise ValueError('CORE_METADATA_CONTRACT')
    utc(core['event_timestamp'])
    z=core['zero_execution_counts']
    if type(z) is not dict or set(z)!={'actions','attempts','grants','budgets','strategies'} or any(type(v) is not int or v!=0 for v in z.values()):
        raise ValueError('CORE_ZERO_COUNTS')


def validate_review(d, *, now=None):
    if type(d) is not dict or set(d)!=REVIEW_KEYS:raise ValueError('REVIEW_SCHEMA')
    if type(d['schema_version']) is not int or d['schema_version']!=1:raise ValueError('REVIEW_VERSION')
    if d['reviewer_origin']!='NANA_INDEPENDENT_HOST_REVIEW' or d['confirmation']!='INDEPENDENTLY_REVIEWED_EXACT_ONE_SHOT':
        raise ValueError('INDEPENDENT_REVIEW_REQUIRED')
    for k in ('operator_authorization_digest','host_metadata_evidence_digest'):
        if type(d[k]) is not str or not HEX.fullmatch(d[k]) or d[k]=='0'*64:raise ValueError('REVIEW_EVIDENCE_HASH_REQUIRED')
    r=parse_receipt(d['receipt'])
    if r.review_provenance is not Provenance.ASTRBOT_REAL_MESSAGE:raise ValueError('FIXTURE_PROMOTION_BLOCKED')
    if d['operator_authorization_digest']!=r.authorization_digest:raise ValueError('OPERATOR_AUTHORIZATION_SCOPE')
    if d['review']!=review_document(r) or digest(d['review'])!=r.review_receipt_digest:raise ValueError('REVIEW_DIGEST_MISMATCH')
    if d['kind']=='AUTHORIZATION_REVIEW':
        if d['runtime_report'] is not None:raise ValueError('PREMATURE_RUNTIME_PROOF')
        now=now or datetime.now(timezone.utc)
        if utc(r.issued_at)>now+timedelta(seconds=2) or utc(r.expires_at)<=now:raise ValueError('RECEIPT_NOT_LIVE')
        mode='ONE_SHOT';proof={}
    elif d['kind']=='RUNTIME_PROOF_REVIEW':
        report=d['runtime_report']
        if type(report) is not dict or set(report)!=REPORT_KEYS:raise ValueError('RUNTIME_REPORT_SCHEMA')
        if (report['schema_version']!=1 or type(report['schema_version']) is not int
            or report['receipt_id']!=r.receipt_id or report['receipt_digest']!=r.receipt_digest
            or report['trust_domain']!='PRODUCTION' or report['source_provenance']!='ASTRBOT_REAL_MESSAGE'
            or report['binding_evidence_digest']!=d['host_metadata_evidence_digest']
            or report['observer_callback_received'] is not True or report['sanitizer_accepted'] is not True):
            raise ValueError('RUNTIME_PROVENANCE_SCOPE')
        z=report['noncore_zero']
        if type(z) is not dict or set(z)!=ZERO_KEYS or any(type(x) is not int or x!=0 for x in z.values()):
            raise ValueError('INDEPENDENT_ZERO_EVIDENCE_REQUIRED')
        # Full persisted Core/ledger/linkage proof still runs on the host later.
        validate_core_metadata(report['core'])
        mode='VERIFY_ONLY';proof={digest(report):d['host_metadata_evidence_digest']}
    else:raise ValueError('REVIEW_KIND')
    return r,mode,proof


def render_seal(r,mode,proof,sha):
    """Data-only Python literals, never embed executable text from reviewer input."""
    if mode not in ('ONE_SHOT','VERIFY_ONLY'):raise ValueError('SEAL_MODE')
    values={'SEAL_MODE':mode,'PRODUCTION_REVIEW_PINS':{r.review_receipt_digest:r.authorization_digest},
            'REAL_RUNTIME_PROOF_PINS':proof,'EXACT_RECEIPT_DIGEST':r.receipt_digest,
            'EXACT_STORE_BINDING':r.store_binding,'REVIEW_SOURCE_SHA':sha}
    lines=['# Offline generated, independently reviewed exact one-shot source seal.',
           'from types import MappingProxyType']
    for k,v in values.items():
        literal=repr(v)
        lines.append(k+' = '+('MappingProxyType('+literal+')' if k.endswith('_PINS') else literal))
    return '\n'.join(lines)+'\n'


def seal(base, destination, review_repo, review_sha, review_path):
    """Explicit offline build; NEVER invoked by a worker or observation callback."""
    base=checked_path(base,directory=True);m=verify_package(base)
    verify_bundle(base/'package')
    from . import sealed_trust
    if sealed_trust.SEAL_MODE!='EMPTY':raise ValueError('EMPTY_BUILDER_REQUIRED')
    default_source=Path(__file__).parent/'sealed_trust.py'
    if (base/'package/support/tools/nana_astrbot_shadow/sealed_trust.py').read_bytes()!=default_source.read_bytes():
        raise ValueError('EMPTY_SOURCE_SEAL_REQUIRED')
    if m.get('r042')!='EMPTY_DEFAULT_ONBOARDING_READY':raise ValueError('R042_EMPTY_BASE_REQUIRED')
    if m.get('production_review_pins')!=0 or m.get('real_runtime_proof_pins')!=0:raise ValueError('EMPTY_BASE_REQUIRED')
    if (base/'data').exists():raise ValueError('RUNTIME_DATA_IN_BUILD_BASE')
    review=source_review(review_repo,review_sha,review_path);r,mode,proof=validate_review(review)
    out=checked_path(destination,directory=True,missing=True)
    if out.exists():raise ValueError('NEW_CANDIDATE_REQUIRED')
    shutil.copytree(base,out);out.chmod(0o700)
    module=out/'package/support/tools/nana_astrbot_shadow/sealed_trust.py'
    module.write_text(render_seal(r,mode,proof,review_sha))
    private_file(out/'source_review.json',review)
    private_file(out/'review.json',review['review'])
    (out/'receipt.json').write_text(r.canonical());(out/'receipt.json').chmod(0o600)
    m.update(base_manifest_sha256=digest((base/'manifest.json').read_bytes()),r042='SEALED_CANDIDATE_NOT_RUNTIME_VERIFIED',seal_mode=mode,production_review_pins=1,
        production_trust_pins=1,real_runtime_proof_pins=len(proof),review_source_SHA=review_sha,
        review_source_path=review_path,review_source_digest=digest(review),
        exact_receipt_digest=r.receipt_digest,exact_store_binding=r.store_binding,
        seal_source_sha256=digest(module.read_bytes()),runtime_verification='NOT_RUN')
    return finalize(out,m)


def finalize(root,manifest):
    manifest['files']={str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*')
                       if p.is_file() and p.name not in ('manifest.json','SHA256SUMS')}
    private_file(root/'manifest.json',manifest,replace=True)
    (root/'SHA256SUMS').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(manifest['files'].items()))+
                                 digest((root/'manifest.json').read_bytes())+'  manifest.json\n')
    verify_package(root)
    archive=root.parent/(root.name+'-onboarding.tar.gz')
    with archive.open('xb') as stream:
        with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0,filename='') as gz:
            with tarfile.open(fileobj=gz,mode='w') as tar:
                for p in sorted(root.rglob('*')):
                    if p.is_file():
                        data=p.read_bytes();info=tarfile.TarInfo(root.name+'/'+str(p.relative_to(root)))
                        info.size=len(data);info.mode=0o700 if p.suffix=='.sh' else 0o600;info.mtime=0
                        tar.addfile(info,io.BytesIO(data))
    return {'filename':archive.name,'bytes':archive.stat().st_size,'SHA256':digest(archive.read_bytes()),
            'seal_mode':manifest.get('seal_mode','EMPTY'),'support_source_SHA':manifest['support_source_SHA'],
            'production_review_pins':manifest.get('production_review_pins',0),'real_runtime_proof_pins':manifest.get('real_runtime_proof_pins',0),
            'host_binding':'UNVERIFIED','E12':'NOT_RUN'}


def main(argv=None):
    p=_SafeParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--directory',required=True);q.add_argument('--scope',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('review-document');q.add_argument('--preparation',required=True);q.add_argument('--approval',required=True);q.add_argument('--output',required=True);q.add_argument('--runtime-report')
    q=sub.add_parser('seal');q.add_argument('--base',required=True);q.add_argument('--output',required=True)
    q.add_argument('--review-repo',required=True);q.add_argument('--review-sha',required=True);q.add_argument('--review-path',required=True)
    try:
        a=p.parse_args(argv)
        if a.command=='prepare':result=prepare(a.directory,read_json(a.scope),a.output)
        elif a.command=='review-document':result=make_review(a.preparation,read_json(a.approval),a.output,
            runtime_report=read_json(a.runtime_report) if a.runtime_report else None)
        else:result=seal(a.base,a.output,a.review_repo,a.review_sha,a.review_path)
        print(canonical(result));return 0
    except BaseException:
        print(canonical({'status':'BLOCKED','reason':'R042_ONBOARDING_POLICY','host_binding':'UNVERIFIED'}));return 2
if __name__=='__main__':raise SystemExit(main())
