"""Host-local startup data, never a portable subject/personality configuration."""
import json,os,tempfile,resource
from pathlib import Path
from typing import Literal
from pydantic import Field,model_validator,model_serializer
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from ..contracts import DTO,CoreError
from ..continuity.project_work.port import ProjectMaterial
from ..continuity.privacy import _json_object
from .surfaces import SurfaceBinding
from ..continuity.current_state import ProjectStateBinding
from ..continuity.hands.browser import BrowserEndpoint
from ..continuity.open_life.sources import IntakeSource
from ..continuity.controlled_world.projects import ControlledProject
from .bilibili_life import BilibiliLifeConfig
from .platform_runtime import QQChannelBinding
from .bilibili_runtime import BilibiliChannelBinding

class LifeConfig(DTO):
    schema_version:Literal[1]=1
    revision:int=Field(default=1,ge=1)
    project_root:str
    current_project_state:ProjectStateBinding|None=None
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
    owned_application_profile:str|None=None
    owned_browser_endpoint:BrowserEndpoint|None=None
    timezone:str='UTC'
    quiet_start_local_hour:int=Field(default=23,ge=0,le=23)
    quiet_end_local_hour:int=Field(default=7,ge=0,le=23)
    min_free_disk_mb:int=Field(default=64,ge=1,le=4096)
    log_max_bytes:int=Field(default=262144,ge=4096,le=1048576)
    surface_bindings:tuple[SurfaceBinding,...]=Field(default=(),max_length=16)
    shared_presence:bool=False
    advanced_life:bool=False
    bilibili_life:BilibiliLifeConfig|None=None
    qq_channels:tuple[QQChannelBinding,...]=Field(default=(),max_length=16)
    bilibili_channels:tuple[BilibiliChannelBinding,...]=Field(default=(),max_length=16)
    @model_serializer(mode='wrap')
    def compatible_optional_platforms(self, handler):
        value=handler(self)
        if self.bilibili_life is None:value.pop('bilibili_life',None)
        if not self.qq_channels:value.pop('qq_channels',None)
        if not self.bilibili_channels:value.pop('bilibili_channels',None)
        return value
    record_research_outcomes:bool=False
    world_sources:tuple[IntakeSource,...]=Field(default=(),max_length=16)
    controlled_projects:tuple[ControlledProject,...]=Field(default=(),max_length=4)
    world_source_root:str|None=None
    world_source_interval_seconds:int=Field(default=300,ge=30,le=86400)
    max_state_mb:int=Field(default=256,ge=1,le=4096)
    max_state_growth_mb_per_hour:int=Field(default=32,ge=1,le=1024)
    storage_review_seconds:int=Field(default=60,ge=1,le=3600)
    storage_growth_grace_seconds:int=Field(default=600,ge=0,le=3600)
    storage_growth_window_seconds:int=Field(default=600,ge=1,le=3600)

    @model_validator(mode='after')
    def valid_timezone(self):
        try:ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('IANA timezone required') from None
        if len({b.binding_id for b in self.surface_bindings})!=len(self.surface_bindings):raise ValueError('duplicate surface binding')
        if len({c.channel_id for c in self.qq_channels})!=len(self.qq_channels):raise ValueError('duplicate QQ channel binding')
        if len({c.channel_id for c in self.bilibili_channels})!=len(self.bilibili_channels):raise ValueError('duplicate Bilibili channel binding')
        bindings={b.binding_id:b for b in self.surface_bindings}
        for platform,channels in (('qq.onebot',self.qq_channels),('bilibili.account',self.bilibili_channels)):
            for channel in channels:
                binding=bindings.get(channel.binding_id)
                if (binding is None or binding.platform!=platform or binding.mode!='PLATFORM_ADAPTER_NO_SEND'
                        or channel.enabled and not binding.enabled):raise ValueError('platform channel surface binding mismatch')
        return self
    max_autonomous_materials:int=Field(default=2,ge=0,le=16)
    active_start_utc:int=Field(default=0,ge=0,le=23)
    active_end_utc:int=Field(default=0,ge=0,le=23)
    provider_hosts:tuple[str,...]=()
    remote_privacy:tuple[Literal['PUBLIC','PROJECT','PERSONAL'],...]=()
    provider_timeout_ms:int=Field(default=120000,ge=100,le=600000)
    provider_output_tokens:int=Field(default=1024,ge=64,le=4096)
    provider_context_tokens:int=Field(default=8192,ge=1024,le=65536)
    # Host may choose an explicit operating budget up to the ORIGINAL Runtime
    # ceiling. Defaults and mission-wide reservations remain unchanged.
    provider_calls_per_day:int=Field(default=12,ge=0,le=128)
    provider_calls_per_hour:int=Field(default=24,ge=0,le=128)
    per_provider_calls_per_day:int=Field(default=24,ge=0,le=128)
    provider_cost_ceiling_micro:int=Field(default=0,ge=0,le=100000)
    provider_total_calls_limit:int|None=Field(default=None,ge=0,le=100000)
    provider_total_reserved_cost_micro:int|None=Field(default=None,ge=0,le=1000000000)


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
        import stat
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):raise CoreError('LIFE_CONFIG_REGULAR_FILE_REQUIRED')
            if info.st_uid!=os.geteuid():raise CoreError('LIFE_CONFIG_OWNER_REQUIRED')
            if info.st_mode&0o077:raise CoreError('LIFE_CONFIG_PRIVATE_MODE_REQUIRED')
            raw=stream.read(65537)
        if len(raw)>65536:raise ValueError()
        obj=json.loads(raw,object_pairs_hook=_json_object)
        return LifeConfig.model_validate_json(json.dumps(obj))
    except (OSError,ValueError):raise CoreError('LIFE_CONFIG_INVALID') from None


def update_config(home,config,*,expected_revision):
    """Host-local CAS; no Subject/Manager event or execution authorization."""
    import fcntl
    home=home_path(home);lock=os.open(home/'.life-settings.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=load_config(home)
        if current.revision!=expected_revision or config.revision!=expected_revision+1:raise CoreError('LIFE_CONFIG_REVISION_CONFLICT')
        config=LifeConfig.model_validate_json(config.model_dump_json())
        fd,tmp=tempfile.mkstemp(dir=home,prefix='.life-')
        try:
            with os.fdopen(fd,'w') as stream:stream.write(config.model_dump_json());stream.flush();os.fsync(stream.fileno())
            os.replace(tmp,home/'life.json');directory=os.open(home,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return config
    finally:os.close(lock)


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
