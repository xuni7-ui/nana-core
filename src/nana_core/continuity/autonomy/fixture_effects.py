"""Sealed offline world fixture, not a general file/network/tool adapter.

Only this exact class (not subclasses or user callbacks) may participate in v9
offline ActionKernel tests. Never receives real resource paths or credentials.
The optional JSON file is fixture world state, NOT a second subject Store.
"""
import json,os,re,tempfile
from pathlib import Path
from ...contracts import CoreError,Receipt,Verification
from ...storage import digest,canonical

class OfflineEffectPort:
    def seed_source(self,resource,*,text,locator):
        if not re.fullmatch(r'synthetic://[A-Za-z0-9/._:-]{1,160}',resource) or type(text) is not str or not 1<=len(text)<=4096 or type(locator) is not str or not 1<=len(locator)<=256:raise CoreError('OFFLINE_FIXTURE_INVALID')
        body=self._load();body['workflow_fixture']=True
        body.setdefault('source_fixtures',{})[resource]={'text':text,'locator':locator}
        self._save(body)
    def seed_observation(self,resource,data):
        from ..open_agency.world import LocalWorldRegistry,bounded_data
        LocalWorldRegistry().validate('world.observe',resource,{})
        bounded_data(data);body=self._load();body.setdefault('observables',{})[resource]=data;self._save(body)
    def __init__(self,identity_id,world_path):
        self.identity_id=identity_id;self.path=Path(world_path)
        if not self.path.name.endswith('.fixture.json'):raise CoreError('OFFLINE_FIXTURE_PATH_REQUIRED')
        self.path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        if self.path.parent.stat().st_mode&0o077 or self.path.is_symlink():raise CoreError('OFFLINE_FIXTURE_PRIVATE_PATH_REQUIRED')
        if not self.path.exists():self._save({'effects':{},'resources':{}})

    def _load(self):
        if self.path.is_symlink() or self.path.stat().st_size>1024*1024:raise CoreError('OFFLINE_FIXTURE_CORRUPT')
        return json.loads(self.path.read_text())

    def _save(self,body):
        raw=canonical(body).encode()
        if len(raw)>1024*1024:raise CoreError('OFFLINE_FIXTURE_CAPACITY')
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix='.world-')
        try:
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
            d=os.open(self.path.parent,os.O_DIRECTORY)
            try:os.fsync(d)
            finally:os.close(d)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def _valid(self,inv):
        if inv.capability.startswith('world.'):
            from ..open_agency.world import LocalWorldRegistry
            LocalWorldRegistry().validate(inv.capability,inv.resource,inv.args);return
        if inv.capability not in {'reading.source.read','reading.source.locate','reading.card.create'} or not re.fullmatch(r'synthetic://[A-Za-z0-9/._:-]{1,160}',inv.resource):raise CoreError('OFFLINE_RESOURCE_DENIED')
        if 'source_id' in inv.args and not re.fullmatch(r'synthetic://[A-Za-z0-9/._:-]{1,160}',inv.args['source_id']):raise CoreError('OFFLINE_SOURCE_DENIED')

    def execute(self,inv):
        self._valid(inv);body=self._load();old=body['effects'].get(inv.idempotency_key)
        if old:
            if old['args_hash']!=inv.args_hash:raise CoreError('OFFLINE_EFFECT_COLLISION')
            return Receipt(external_id=inv.idempotency_key,result=old['result'])
        if inv.capability.startswith('world.'):
            from ..open_agency.world import execute_world
            result=execute_world(self,inv)
            body['effects'][inv.idempotency_key]={'args_hash':inv.args_hash,'resource':inv.resource,'result':result}
            body['resources'][inv.resource]=result;self._save(body)
            return Receipt(external_id=inv.idempotency_key,result=result)
        result={'text':inv.args.get('content','A supplied fictional observation'),'resource':inv.resource,'fixture':True}
        if body.get('workflow_fixture'):
            if inv.capability=='reading.card.create':
                result.update(locator=inv.args.get('locator'),source_id=inv.args['source_id'])
            else:
                source=body.get('source_fixtures',{}).get(inv.resource)
                if not source:raise CoreError('OFFLINE_SOURCE_UNAVAILABLE')
                result['text']=source['text']
                if inv.capability=='reading.source.locate':result['locator']=source['locator']
        body['effects'][inv.idempotency_key]={'args_hash':inv.args_hash,'resource':inv.resource,'result':result}
        body['resources'][inv.resource]=result
        self._save(body)
        return Receipt(external_id=inv.idempotency_key,result=result)

    def verify(self,inv):
        self._valid(inv);body=self._load();old=body['effects'].get(inv.idempotency_key)
        if not old:return Verification(verdict='FINAL_NO_EFFECT',evidence={})
        match=old['args_hash']==inv.args_hash and body['resources'].get(inv.resource)==old['result']
        return Verification(verdict='MATCH' if match else 'EFFECT_MISMATCH',evidence={'result':old['result'],'world_digest':digest(body)})
