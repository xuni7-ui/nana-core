"""Host-local startup data, never a portable subject/personality configuration."""
import json,os,tempfile,resource
from pathlib import Path
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError
from ..continuity.project_work.port import ProjectMaterial
from ..continuity.privacy import _json_object

class LifeConfig(DTO):
    schema_version:Literal[1]=1
    project_root:str
    materials:tuple[ProjectMaterial,...]=Field(min_length=1,max_length=16)
    practice:ProjectMaterial
    heldout:ProjectMaterial
    transfer:ProjectMaterial
    max_memory_mb:int=Field(default=512,ge=256,le=1024)
    max_cpus:int=Field(default=4,ge=1,le=4)
    idle_review_seconds:int=Field(default=60,ge=10,le=3600)
    activity_interval_seconds:float=Field(default=3,ge=.5,le=3600)
    document_learning:tuple[ProjectMaterial,...]=Field(default=(),max_length=3)
    allow_local_skills:bool=False
    max_autonomous_materials:int=Field(default=2,ge=0,le=16)
    active_start_utc:int=Field(default=0,ge=0,le=23)
    active_end_utc:int=Field(default=0,ge=0,le=23)
    provider_hosts:tuple[str,...]=()
    remote_privacy:tuple[Literal['PUBLIC','PROJECT','PERSONAL'],...]=()
    provider_timeout_ms:int=Field(default=2000,ge=100,le=3000)
    provider_calls_per_day:int=Field(default=12,ge=0,le=24)
    provider_cost_ceiling_micro:int=Field(default=0,ge=0,le=100000)


def home_path(home):
    p=Path(home).absolute()
    if p!=p.resolve():raise CoreError('LIFE_HOME_SYMLINK_DENIED')
    p.mkdir(parents=True,mode=0o700,exist_ok=True)
    if p.stat().st_mode&0o077:raise CoreError('LIFE_PRIVATE_HOME_REQUIRED')
    return p


def write_config(home,config):
    p=home_path(home)/'life.json'
    if p.exists():raise CoreError('LIFE_ALREADY_INITIALIZED')
    fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.life-')
    try:
        with os.fdopen(fd,'w') as stream:stream.write(config.model_dump_json());stream.flush();os.fsync(stream.fileno())
        # Creation only. Never replace somebody else's initialized home.
        os.link(tmp,p);directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:os.unlink(tmp)


def load_config(home):
    home=home_path(home);p=home/'life.json'
    try:
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:raw=stream.read(65537)
        if len(raw)>65536 or p.stat().st_mode&0o077:raise ValueError()
        obj=json.loads(raw,object_pairs_hook=_json_object)
        return LifeConfig.model_validate_json(json.dumps(obj))
    except (OSError,ValueError):raise CoreError('LIFE_CONFIG_INVALID') from None


def apply_resource_limits(config):
    current=sorted(os.sched_getaffinity(0));selected=current[:config.max_cpus]
    os.sched_setaffinity(0,selected)
    ceiling=config.max_memory_mb*1024*1024
    old=resource.getrlimit(resource.RLIMIT_AS)
    ceiling=min(ceiling,old[1]) if old[1]!=resource.RLIM_INFINITY else ceiling
    resource.setrlimit(resource.RLIMIT_AS,(ceiling,ceiling))
    def cgroup(name):
        try:return (Path('/sys/fs/cgroup')/name).read_text().strip()
        except OSError:return 'UNKNOWN'
    return {'affinity_cpus':len(selected),'memory_address_space_limit_mb':ceiling//1024//1024,'cgroup_memory_max':cgroup('memory.max'),'cgroup_cpu_max':cgroup('cpu.max'),'local_large_model':'DISABLED','capture':'DISABLED'}
