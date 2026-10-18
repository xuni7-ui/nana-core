"""Explicit, host-bound controlled screen capture. No platform discovery or consent UI.

A backend is an application capability, never chosen by a model. This V1 only
admits PUBLIC pixels from an owned OS test window; no ambient desktop fallback.
"""
import hashlib
from typing import Literal, Protocol
from pydantic import Field, model_validator
from ...contracts import DTO, CoreError
from ...storage import digest
from .contracts import CapturedMedia, SourceDescription, capture_identity

class ScreenBackendDescriptor(DTO):
    backend_id: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    session_kind: Literal['OWNED_X11_DUMMY'] = 'OWNED_X11_DUMMY'
    capture_scope: Literal['EXPLICIT_WINDOW'] = 'EXPLICIT_WINDOW'
    supports_window: Literal[True] = True
    supports_region: Literal[False] = False
    supports_full_desktop: Literal[False] = False
    consent: Literal['EXPLICIT_HOST_BINDING'] = 'EXPLICIT_HOST_BINDING'
    controlled_surface: Literal[True] = True
    image_format: Literal['PNG'] = 'PNG'
    max_pixels: int = Field(default=500000, ge=1, le=500000)

class ScreenCaptureReceipt(DTO):
    source_profile_id: str
    source_revision: int = Field(ge=1)
    backend_id: str
    session_binding_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    capture_scope: Literal['EXPLICIT_WINDOW'] = 'EXPLICIT_WINDOW'
    origin: Literal['REAL_OS_CONTROLLED'] = 'REAL_OS_CONTROLLED'
    started_at_us: int = Field(ge=0)
    completed_at_us: int = Field(ge=0)
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    encoded_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    pixel_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    status: Literal['CAPTURED'] = 'CAPTURED'
    @model_validator(mode='after')
    def valid(self):
        if self.completed_at_us < self.started_at_us or self.width*self.height>500000:raise ValueError('screen receipt bound')
        return self

class ControlledScreenBackend(Protocol):
    binding_digest: str
    def geometry(self) -> tuple[int,int]: ...
    def capture(self, geometry: tuple[int,int]) -> tuple[bytes,str]: ...

class RealScreenPerceptionPort:
    def __init__(self, backend, descriptor, profile, clock, *, host_enabled=False):
        if type(descriptor) is not ScreenBackendDescriptor:raise CoreError('SCREEN_BACKEND_DESCRIPTOR_REQUIRED')
        if not host_enabled:raise CoreError('SCREEN_HOST_DISABLED')
        if profile.source_kind!='SCREEN' or profile.modality!='IMAGE' or profile.privacy_class!='PUBLIC':raise CoreError('SCREEN_SCOPE_DENIED')
        self._backend,self._descriptor,self._profile,self._clock=backend,descriptor,profile,clock
        self._invalid=None;self._geometry=backend.geometry();self._binding=backend.binding_digest;self._sequence=0
        if self._geometry[0]*self._geometry[1]>descriptor.max_pixels:raise CoreError('SCREEN_SIZE_BOUND')
    def describe(self):
        return SourceDescription(adapter_identity=self._descriptor.backend_id,source_kind='SCREEN',modalities=('IMAGE',),max_bytes=self._profile.max_capture_bytes)
    def backend_projection(self):
        return {**self._descriptor.model_dump(mode='json'),'health':self.health(),'binding_status':'HOST_BOUND','qualification_level':'L1_REAL_OS_CONTROLLED_NOT_PHYSICAL_DESKTOP'}
    def _check(self):
        if self._invalid:raise CoreError(self._invalid)
        if self._backend.binding_digest!=self._binding:self._invalid='SCREEN_SESSION_CHANGED'
        elif self._backend.geometry()!=self._geometry:self._invalid='SCREEN_TOPOLOGY_CHANGED'
        if self._invalid:raise CoreError(self._invalid)
    def health(self):
        try:self._check();return 'AVAILABLE'
        except CoreError as exc:return exc.code
        except Exception:return 'SCREEN_SESSION_UNAVAILABLE'
    def capture(self, request):
        p=self._profile
        if (request.source_profile_id,request.source_revision,request.requested_modality,request.privacy_class)!=(p.source_profile_id,p.revision,'IMAGE','PUBLIC'):raise CoreError('SCREEN_BINDING_STALE')
        start=self._clock.utc_now_us()
        if start>=request.deadline_us:raise CoreError('CAPTURE_DEADLINE_EXPIRED')
        self._check()
        try:data,pixels=self._backend.capture(self._geometry)
        except CoreError:raise
        except Exception:raise CoreError('SCREEN_CAPTURE_UNKNOWN') from None
        self._check();end=self._clock.utc_now_us()
        if end>request.deadline_us:raise CoreError('SCREEN_CAPTURE_UNKNOWN')
        if type(data) is not bytes or not 0<len(data)<=min(p.max_capture_bytes,request.max_capture_bytes):raise CoreError('SCREEN_CAPTURE_SIZE_BOUND')
        # Validate the backend's pixel claim from the actual encoded capture too.
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            if im.format!='PNG' or im.size!=self._geometry or hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()!=pixels:raise CoreError('SCREEN_PIXEL_INTEGRITY')
        sha=hashlib.sha256(data).hexdigest();self._sequence+=1
        receipt=ScreenCaptureReceipt(source_profile_id=p.source_profile_id,source_revision=p.revision,backend_id=self._descriptor.backend_id,session_binding_digest=self._binding,started_at_us=start,completed_at_us=end,width=self._geometry[0],height=self._geometry[1],encoded_digest=sha,pixel_digest=pixels)
        event='screen.'+digest([request.request_id,self._binding])
        return CapturedMedia(capture_id=capture_identity(p.source_profile_id,p.revision,event,start,self._sequence,sha),source_profile_id=p.source_profile_id,source_revision=p.revision,source_event_id=event,modality='IMAGE',event_time_us=start,observed_time_us=end,byte_digest=sha,byte_length=len(data),coverage='EXPLICIT_OWNED_WINDOW_ONLY',sequence=self._sequence,privacy_class='PUBLIC',data=data,origin='REAL_OS_CONTROLLED',screen_receipt=receipt.model_dump(mode='json'))
