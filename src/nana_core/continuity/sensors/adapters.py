"""Injected sources only. No device enumeration, dynamic imports or shell sensors."""
import hashlib,os,stat
from pathlib import Path
from ...contracts import CoreError
from .contracts import *

def captured(request,data,clock,*,event_time=None,sequence=None,event_id=None):
    now=clock.utc_now_us();event_time=now if event_time is None else event_time
    sequence=request.requested_at_us if sequence is None else sequence;event_id=event_id or request.request_id
    sha=hashlib.sha256(data).hexdigest()
    return CapturedMedia(capture_id=capture_identity(request.source_profile_id,request.source_revision,event_id,event_time,sequence,sha),source_profile_id=request.source_profile_id,source_revision=request.source_revision,source_event_id=event_id,modality=request.requested_modality,event_time_us=event_time,observed_time_us=now,byte_digest=sha,byte_length=len(data),coverage='BOUNDED_SAMPLE',sequence=sequence,privacy_class=request.privacy_class,data=data)

class SyntheticSourceAdapter:
    def __init__(self,clock,data,*,kind='SYNTHETIC',modality='IMAGE'):
        self.clock,self.data,self.kind,self.modality=clock,data,kind,modality;self.bytes_read=0;self.captures=0;self.pending={}
    def describe(self):return SourceDescription(adapter_identity='synthetic.source-v1',source_kind=self.kind,modalities=(self.modality,),max_bytes=16777216)
    def health(self):return 'AVAILABLE'
    def publish(self,key,data,*,event_time,sequence):self.pending={key:(data,event_time,sequence)}
    def capture(self,request):
        if type(request) is not ObservationRequest:raise CoreError('CAPTURE_TYPED_REQUEST_REQUIRED')
        if request.sample_key:
            if request.sample_key not in self.pending:raise CoreError('SOURCE_SAMPLE_EXPIRED')
            data,event,seq=self.pending.pop(request.sample_key)
        else:data=self.data;event=self.clock.utc_now_us();seq=request.requested_at_us
        self.bytes_read+=len(data);self.captures+=1
        return captured(request,data,self.clock,event_time=event,sequence=seq,event_id=request.sample_key or request.request_id)
class SyntheticScreenAdapter(SyntheticSourceAdapter):
    def __init__(self,clock,data):super().__init__(clock,data,kind='SCREEN')
class SyntheticCameraAdapter(SyntheticSourceAdapter):
    def __init__(self,clock,data):super().__init__(clock,data,kind='CAMERA')
class SyntheticMicrophoneAdapter(SyntheticSourceAdapter):
    def __init__(self,clock,data):super().__init__(clock,data,kind='MICROPHONE',modality='AUDIO')

class FileImportAdapter:
    """Application pins one flat regular file under a trusted root. No selected path in DTO."""
    def __init__(self,clock,root,filename,*,modality='IMAGE',max_bytes=16777216):
        self.clock,self.root,self.filename,self.modality,self.max_bytes=clock,Path(root),filename,modality,max_bytes;self.bytes_read=0
        if not isinstance(filename,str) or filename in {'.','..'} or '/' in filename or '\\' in filename or '\x00' in filename:raise CoreError('SOURCE_PATH_DENIED')
        # Refuse any symlink ancestor, not just the final path.
        absolute=self.root.absolute()
        if any(p.is_symlink() for p in [absolute,*absolute.parents]):raise CoreError('SOURCE_PATH_DENIED')
    def describe(self):return SourceDescription(adapter_identity='file.import-v1',source_kind='FILE_IMPORT',modalities=(self.modality,),max_bytes=self.max_bytes)
    def health(self):return 'AVAILABLE' if self.root.is_dir() else 'UNAVAILABLE'
    def capture(self,request):
        if type(request) is not ObservationRequest:raise CoreError('CAPTURE_TYPED_REQUEST_REQUIRED')
        try:
            directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
            try:
                for component in self.root.absolute().parts[1:]:
                    if component in {'.','..'}:raise CoreError('SOURCE_PATH_DENIED')
                    following=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                    os.close(directory);directory=following
            except BaseException:
                os.close(directory);raise
            try:
                fd=os.open(self.filename,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW,dir_fd=directory)
                with os.fdopen(fd,'rb') as f:
                    info=os.fstat(f.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or not 1<=info.st_size<=min(self.max_bytes,request.max_capture_bytes):raise CoreError('SOURCE_FILE_DENIED')
                    data=f.read(min(self.max_bytes,request.max_capture_bytes)+1);self.bytes_read+=len(data)
                    if len(data)>self.max_bytes:raise CoreError('SOURCE_FILE_DENIED')
            finally:os.close(directory)
        except OSError:raise CoreError('SOURCE_UNAVAILABLE') from None
        return captured(request,data,self.clock)
