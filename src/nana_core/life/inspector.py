"""Local, read-only, bounded metadata projection of the existing Subject database.

No Store constructor, writer lock, authority, prompt, provider or repair path.
Recorded thoughts and surprise content are never rendered. Existing source-backed
projectors are reused through a non-writing read adapter, not a second state store.
"""
import argparse,json,os,re,sqlite3,stat,time
from pathlib import Path
from typing import Literal
from ..clock import Clock
from ..contracts import DTO,CoreError
from ..storage import digest
from ..storage.sqlite_store import Store,KEYS
from ..storage.development_schema import keys_for
from ..continuity.privacy import PrivacyJournal,_load
from ..continuity.records import RecordService
from ..continuity.autonomy.relationships import relationship_influence
from ..continuity.relational.projections import social_appetite
from ..continuity.subject.experience_need import project_need


class InspectorItem(DTO):
    category:str
    reference:str
    state:str
    record_id:str|None=None
    as_of_us:int|None=None
    source_memory_ids:tuple[str,...]=()


class InspectorSnapshot(DTO):
    schema_version:Literal[1]=1
    derived:Literal[True]=True
    read_only:Literal[True]=True
    identity_id:str
    as_of_us:int
    coverage:Literal['BOUNDED_METADATA_ONLY']='BOUNDED_METADATA_ONLY'
    sections:dict[str,tuple[InspectorItem,...]]
    resources:dict[str,int]|None=None
    private_activity:Literal['UNKNOWN_CONTENT_NOT_EXPOSED','PRESENT_CONTENT_WITHHELD','NONE_IN_BOUNDED_VIEW']='UNKNOWN_CONTENT_NOT_EXPOSED'
    governance_visibility:Literal['LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE']='LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE'
    execution_authority:Literal[False]=False
    self_view:dict|None=None
    advanced_life:dict|None=None


def _regular(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid():raise CoreError('INSPECTOR_PATH_DENIED')


def _token(value):
    return value if type(value) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}',value) else 'UNKNOWN'


class _ReadView:
    """Only existing Store read primitives; no transaction or mutation methods."""
    def __init__(self,db,path,scope,privacy):
        self.db,self.path,self.scope,self.allowed=db,path,scope,privacy
        self.clock=Clock();self.schema_target=db.execute('PRAGMA user_version').fetchone()[0]
        if self.schema_target!=13:raise CoreError('INSPECTOR_SCHEMA_UNSUPPORTED')
        self.keys={**KEYS,**keys_for(self.schema_target)}
        identities=db.execute('SELECT * FROM identities LIMIT 2').fetchall()
        if len(identities)!=1:raise CoreError('INSPECTOR_LINEAGE_AMBIGUOUS')
        self.identity=dict(identities[0])
        sidecar=Path(str(path)+'.privacy.json');_regular(sidecar)
        link=_load(sidecar);anchor=Path(link['anchor_path']) if 'anchor_path' in link else sidecar
        _regular(anchor)
        journal=object.__new__(PrivacyJournal);journal.path=anchor;journal.store=self
        self.privacy=journal;self.fingerprint=digest(journal.read())
        self.ensure_privacy_current()
    def ensure_privacy_current(self):
        body=self.privacy.read()
        if digest(body)!=self.fingerprint:raise CoreError('INSPECTOR_SOURCE_CHANGED')
        if sum(len(x['memory_ids'])+len(x['evidence_ids']) for x in body['intents'])>1024:raise CoreError('INSPECTOR_PRIVACY_REVIEW_BOUND')
        # Purge is one SQL transaction per journal intent. Pending roots mean an
        # interrupted purge/old restored snapshot: refuse to project, never repair.
        for intent in body['intents']:
            for table,column,ids in (('memories','lifecycle',intent['memory_ids']),('continuity_evidence','state',intent['evidence_ids'])):
                for key in ids:
                    row=Store.one(self,table,key)
                    if row and row[column]!='DELETED':raise CoreError('INSPECTOR_PRIVACY_RECONCILIATION_REQUIRED')
    def one(self,table,key):
        row=Store.one(self,table,key)
        if row and table in {'memories','continuity_records','continuity_evidence'}:
            if row.get('scope',self.scope)!=self.scope or row['privacy_class'] not in self.allowed:return None
        return row
    def artifact(self,key):
        size=self.db.execute('SELECT length(payload) FROM artifacts WHERE artifact_id=?',(key,)).fetchone()
        if not size or size[0] is None or size[0]>131072:raise CoreError('INSPECTOR_PAYLOAD_UNAVAILABLE')
        return Store.artifact(self,key)
    def all(self,table):
        if table not in self.keys:raise ValueError('INSPECTOR_TABLE_DENIED')
        rows=self.db.execute('SELECT * FROM '+table+' ORDER BY rowid LIMIT 257').fetchall()
        if len(rows)>256:raise CoreError('INSPECTOR_PROJECTION_HORIZON')
        return [dict(row) for row in rows if 'record_id' not in row.keys() or self.one('continuity_records',row['record_id'])]


def inspect(home,*,scope,entity_id,privacy=('PUBLIC','PROJECT'),limit=16):
    if type(limit) is not int or not 1<=limit<=32 or not privacy or set(privacy)-{'PUBLIC','PROJECT','PERSONAL'}:raise CoreError('INSPECTOR_POLICY_DENIED')
    home=Path(home).absolute()
    if home!=home.resolve() or home.stat().st_uid!=os.getuid() or home.stat().st_mode&0o077:raise CoreError('INSPECTOR_PRIVATE_HOME_REQUIRED')
    path=home/'subject/self.db'
    for suffix in ('','-wal','-shm','.privacy.json'):
        p=Path(str(path)+suffix)
        if p.exists() or p.is_symlink():_regular(p)
    # SQLite URI quoting preserves literal ?, # and spaces in the owned path.
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.2,isolation_level=None)
    db.row_factory=sqlite3.Row;started=time.monotonic();steps=0
    def budget():
        nonlocal steps
        steps+=1000
        return int(steps>2_000_000 or time.monotonic()-started>1)
    db.set_progress_handler(budget,1000)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        view=_ReadView(db,path,scope,tuple(privacy));records=RecordService(view)
        sections={name:[] for name in ('runtime','goals','activities','concerns','needs','affect','relationship','interests','suppressed_deferred','decisions','experience','provenance','authority','unknown','provider','queue','source_lifecycle','health','private_intents','skills','world','learning')}
        def item(section,category,reference,state,record=None,as_of=None,refs=()):
            if len(sections[section])<limit:sections[section].append(InspectorItem(category=category,reference=reference,state=_token(state),record_id=record,as_of_us=as_of,source_memory_ids=tuple(refs)[:32]))
        def visible(rid):
            row=view.one('continuity_records',rid)
            return bool(row and row['lifecycle']=='ACTIVE' and records.current_support(rid))
        lease=db.execute('SELECT * FROM runtime_lease LIMIT 1').fetchone()
        resources=None
        if lease:item('runtime','LEASE_EPOCH',str(lease['epoch']),lease['state'],as_of=lease['heartbeat_at_us'])
        if lease and lease['state']=='ACTIVE':
            from ..presence.authority import process_identity
            try:
                if process_identity(lease['pid'])==(lease['process_start'],lease['boot_id']):
                    values={}
                    for line in Path('/proc/'+str(lease['pid'])+'/status').read_text().splitlines():
                        if line.startswith(('VmRSS:','Threads:')):values[line.split(':')[0]]=int(line.split()[1])
                    if process_identity(lease['pid'])==(lease['process_start'],lease['boot_id']):resources=values
            except (OSError,ValueError):pass
        # Indexed finite record candidates; only typed state fields leave process.
        kinds={'INTENTION':'activities','OPEN_CONCERN':'concerns','INTENTION_DISPOSITION':'suppressed_deferred','CONSTRAINT_OUTCOME':'authority','ASSERTION':'interests','CODE_SKILL':'authority','DISCLOSURE_DECISION':'activities'}
        marks=','.join('?' for _ in privacy)
        for kind,section in kinds.items():
            if kind=='OPEN_CONCERN':
                # The proposal payload is historical, not the concern's current
                # lifecycle. Show one authoritative row per concern; prior
                # revisions must not crowd out or mislabel its current state.
                rows=db.execute('SELECT r.record_id,c.updated_at_us AS created_at_us,c.state AS concern_state FROM open_concerns c JOIN continuity_records r ON c.record_id=r.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+") AND r.lifecycle='ACTIVE' ORDER BY c.updated_at_us DESC,c.rowid DESC LIMIT ?",(scope,*privacy,limit)).fetchall()
            else:
                rows=db.execute('SELECT record_id,created_at_us FROM continuity_records WHERE record_kind=? AND scope=? AND privacy_class IN ('+marks+") AND lifecycle='ACTIVE' ORDER BY created_at_us DESC LIMIT ?",(kind,scope,*privacy,limit)).fetchall()
            for row in rows:
                rid=row['record_id']
                if not visible(rid):continue
                body=records.read(rid)['payload']
                state=row['concern_state'] if kind=='OPEN_CONCERN' else body.get('state',body.get('disposition',body.get('code',body.get('result',body.get('kind','UNKNOWN')))))
                refs=records.support(rid)
                item(section,kind,rid,state,rid,row['created_at_us'],refs)
                item('provenance',kind,rid,'CURRENT_SUPPORT',rid,row['created_at_us'],refs)
        for row in db.execute('SELECT c.* FROM subject_cycles c JOIN continuity_records r ON c.record_id=r.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+') ORDER BY c.revision DESC LIMIT ?',(scope,*privacy,limit)):
            if visible(row['record_id']):
                rid=row['record_id'];refs=records.support(rid)
                item('decisions','JUDGMENT',row['cycle_id'],row['judgment'],rid,row['created_at_us'],refs)
                body=records.read(rid)['payload']
                # WHAT/WHY codes and source links; never purpose/reason/wording
                # or raw model proposals, even for a legitimately visible cycle.
                for block,key in (('motivation','source'),('intention','behavior'),('evaluation','normative')):
                    value=body.get(block)
                    if type(value) is dict:item('decisions',block.upper(),row['cycle_id'],value.get(key),rid,row['created_at_us'],refs)
        for row in db.execute('SELECT c.request_id,c.state,c.record_id,c.created_at_us FROM cognitive_requests c JOIN continuity_records r ON c.record_id=r.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+') ORDER BY c.created_at_us DESC LIMIT ?',(scope,*privacy,limit)):
            # Operational attempt state survives source erasure; no proposal/body
            # is revived and this is never a claim of current semantic support.
            item('provider','COGNITION_ATTEMPT',row['request_id'],row['state'],row['record_id'],row['created_at_us'])
        # Goals carry no privacy column: expose only IDs/state linked by a visible
        # current adopted-goal record. Never render body_json/objective/surprise.
        for row in db.execute("SELECT g.goal_id,g.state,r.record_id FROM goals g JOIN continuity_records r ON r.record_id=json_extract(g.body_json,'$.record_id') AND r.record_kind='ADOPTED_GOAL' WHERE r.scope=? ORDER BY g.rowid DESC LIMIT ?",(scope,limit)):
            if visible(row['record_id']):item('goals','GOAL',row['goal_id'],row['state'],row['record_id'])
        for row in db.execute('SELECT e.experience_id,e.record_id,e.outcome,e.created_at_us FROM experiences e JOIN continuity_records r ON r.record_id=e.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+') ORDER BY e.created_at_us DESC LIMIT ?',(scope,*privacy,limit)):
            if visible(row['record_id']):item('experience','VERIFIED_OUTCOME',row['experience_id'],row['outcome'],row['record_id'],row['created_at_us'])
        for row in db.execute('SELECT l.lesson_id,l.record_id,l.state FROM lessons l JOIN continuity_records r ON r.record_id=l.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+') ORDER BY l.rowid DESC LIMIT ?',(scope,*privacy,limit)):
            if visible(row['record_id']):item('learning','METHOD_LESSON',row['lesson_id'],row['state'],row['record_id'])
        for row in db.execute('SELECT DISTINCT task_class FROM experiences ORDER BY created_at_us DESC LIMIT 8'):
            need=project_need(view,row[0],scope=scope,privacy_classes=privacy)
            item('needs','EXPERIENCE_NEED',digest(row[0])[:16],need.state,need.source_record_ids[0] if need.source_record_ids else None)
        appetite=social_appetite(view,scope=scope,privacy_classes=privacy)
        item('affect','SOCIAL_APPETITE','derived',appetite.state,appetite.source_record_ids[0] if appetite.source_record_ids else None,appetite.as_of_us,appetite.source_memory_ids)
        relation=relationship_influence(view,entity_id,scope=scope,privacy_classes=privacy)
        for name in ('familiarity','care_salience','boundary_salience','repair_tension','interaction_latitude','shared_commitment_relevance'):
            facet=getattr(relation,name);item('relationship',name,'derived',facet.assessment,facet.support_refs[0] if facet.support_refs else None,relation.as_of_us)
        for facet in relation.trust:item('relationship','trust',digest(facet.domain)[:16],facet.assessment,facet.support_refs[0] if facet.support_refs else None,relation.as_of_us)
        from ..continuity.autonomy.private_intent import metadata
        private=metadata(view,scope,privacy)
        for value in private:
            item('private_intents',value['category'],value['intent_id'],value['status'],value['record_id'])
            item('private_intents','DISCLOSURE_POLICY',value['intent_id'],value['disclosure_policy'],value['record_id'])
            item('private_intents','RISK',value['intent_id'],value['risk_class'],value['record_id'])
            item('private_intents','AUTHORITY_REQUIRED',value['intent_id'],value['authority_need'],value['record_id'])
        for row in db.execute('SELECT b.* FROM world_beliefs b JOIN continuity_records r ON b.record_id=r.record_id WHERE r.scope=? AND r.privacy_class IN ('+marks+') ORDER BY b.known_at_us DESC LIMIT ?',(scope,*privacy,limit)):
            item('world','WORLD_BELIEF',row['belief_id'],row['state'] if visible(row['record_id']) else 'UNKNOWN_SUPPORT_WITHDRAWN',row['record_id'],row['known_at_us'])
        for row in db.execute("SELECT record_id FROM continuity_records WHERE scope=? AND record_kind='CODE_SKILL' AND lifecycle='ACTIVE' ORDER BY created_at_us DESC LIMIT ?",(scope,limit)):
            head=view.one('continuity_records',row['record_id'])
            if head:item('skills','CODE_SKILL',row['record_id'],'CURRENT_SUPPORT' if visible(row['record_id']) else 'UNAVAILABLE_OR_RETIRED',row['record_id'])
        for row in db.execute('SELECT action_id,state FROM actions ORDER BY rowid DESC LIMIT ?',(limit,)):
            item('authority','ACTION',row['action_id'],row['state'])
        for row in db.execute('SELECT grant_id,revoked FROM grants ORDER BY rowid DESC LIMIT ?',(limit,)):
            item('authority','GRANT',row['grant_id'],'REVOKED' if row['revoked'] else 'INSTALLED_SCOPE_NOT_SHOWN')
        for row in db.execute('SELECT memory_id,lifecycle,updated_at_us FROM memories WHERE scope=? AND privacy_class IN ('+marks+') ORDER BY updated_at_us DESC LIMIT ?',(scope,*privacy,limit)):
            item('source_lifecycle','MEMORY',row['memory_id'],row['lifecycle'],as_of=row['updated_at_us'])
        # Operational counts only. Never query arguments, grant bodies or reasons.
        for state,count in db.execute('SELECT state,count(*) FROM runtime_queue GROUP BY state'):
            item('queue','STATE_COUNT',str(count),state)
        for state,count in db.execute("SELECT state,count(*) FROM actions WHERE state IN ('UNKNOWN','BLOCKED') GROUP BY state"):
            item('unknown' if state=='UNKNOWN' else 'authority','ACTION_COUNT',str(count),state)
        item('health','INSPECTOR_READ','snapshot','READ_ONLY')
        view.ensure_privacy_current()
        for name,values in sections.items():
            if not values:item(name,'COVERAGE','none','UNKNOWN')
        from ..continuity.person_self import project,compact
        from ..continuity.lived_language import expression_policy
        personal=project(view,entity_id=entity_id,scope=scope,privacy=privacy)
        summary=compact(personal)
        summary['recent_exchanges']=[]  # Inspector never becomes a transcript reader.
        summary['learned_expression']=expression_policy(view,scope=scope,privacy=privacy,mode='CASUAL')
        summary['source_record_ids']=personal['source_record_ids']
        from ..continuity.open_life.projections import advanced_view
        from ..continuity.open_life.opportunities import projection
        advanced={**advanced_view(view,scope=scope,privacy=privacy),'opportunities':projection(view,(scope,),privacy)}
        return InspectorSnapshot(identity_id=view.identity['identity_id'],as_of_us=view.clock.utc_now_us(),sections={k:tuple(v) for k,v in sections.items()},resources=resources,private_activity='PRESENT_CONTENT_WITHHELD' if private else 'UNKNOWN_CONTENT_NOT_EXPOSED',self_view=summary,advanced_life=advanced)
    except (sqlite3.Error,OSError,ValueError,TypeError,KeyError):raise CoreError('INSPECTOR_UNAVAILABLE_FAIL_CLOSED') from None
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);p.add_argument('--scope',required=True);p.add_argument('--entity',required=True);a=p.parse_args()
    try:print(inspect(a.home,scope=a.scope,entity_id=a.entity).model_dump_json())
    except (CoreError,OSError) as exc:
        print(json.dumps({'state':'UNKNOWN','code':exc.code if isinstance(exc,CoreError) else 'INSPECTOR_UNAVAILABLE_FAIL_CLOSED','read_only':True}));raise SystemExit(2) from None
if __name__=='__main__':main()
