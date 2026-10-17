"""Actual bounded image/audio/video byte decoding, not JSON video fixtures.

Technical perception is real local processing. Semantic interpretation/transcription
remains UNKNOWN unless an independently supplied reviewed adapter provides it.
"""
import array,hashlib,io,json,math,os,shutil,subprocess,tempfile,warnings
from pathlib import Path
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ...storage import canonical,digest
from ..contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..records import RecordService
from ..providers import MediaProposal,MediaSession

class PublicMediaSource(DTO):
    source_id:str=Field(pattern=r'^[a-z][a-z0-9._:-]{0,95}$')
    modality:Literal['IMAGE','AUDIO','VIDEO']
    origin:Literal['SYNTHETIC','RECORDED']
    event_time_us:int=Field(ge=0)
    observed_time_us:int=Field(ge=0)
    privacy:Literal['PUBLIC']='PUBLIC'
    public_nonpersonal:Literal[True]=True

class MediaDecoder:
    def _run(self,args,*,limit=4*1024*1024,input_root=None):
        if not shutil.which('bwrap'):raise CoreError('MEDIA_SANDBOX_UNAVAILABLE')
        if input_root is None:raise CoreError('MEDIA_INPUT_ROOT_REQUIRED')
        command=['bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--setenv','PATH','/usr/bin','--setenv','LD_LIBRARY_PATH','/usr/lib/x86_64-linux-gnu/blas:/usr/lib/x86_64-linux-gnu/lapack']
        for system in ('/usr/bin','/usr/lib','/usr/lib64','/lib','/lib64'):
            if Path(system).exists():command+=['--ro-bind',system,system]
        if Path('/etc/ld.so.cache').exists():command+=['--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache']
        command+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(input_root),'/input','--chdir','/tmp','/usr/bin/python3','-I','-c',
            'import os,resource,sys;resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912));resource.setrlimit(resource.RLIMIT_CPU,(10,10));resource.setrlimit(resource.RLIMIT_FSIZE,(4194304,4194304));os.execvp(sys.argv[1],sys.argv[1:])']
        args=[str(a).replace(str(input_root)+'/','/input/') for a in args]
        args=command+args
        with tempfile.TemporaryDirectory(prefix='subject-decode-') as d:
            out=Path(d)/'out';err=Path(d)/'err'
            with out.open('wb') as o,err.open('wb') as e:
                try:p=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=o,stderr=e,timeout=12,env={'PATH':os.defpath},check=False)
                except (subprocess.TimeoutExpired,OSError):raise CoreError('MEDIA_DECODER_UNAVAILABLE_OR_TIMEOUT') from None
            if p.returncode:raise CoreError('MEDIA_MALFORMED_OR_UNSUPPORTED')
            if out.stat().st_size>limit:raise CoreError('MEDIA_DECODE_BOUND')
            return out.read_bytes()
    def decode(self,data,modality):
        if type(data) is not bytes or not 1<=len(data)<=16*1024*1024:raise CoreError('MEDIA_BYTE_BOUND')
        if modality=='IMAGE':
            try:
                from PIL import Image,ImageStat
                with warnings.catch_warnings():
                    warnings.simplefilter('error',Image.DecompressionBombWarning)
                    im=Image.open(io.BytesIO(data),formats=('PNG','JPEG','WEBP'))
                    if im.width*im.height>4_000_000:raise CoreError('MEDIA_PIXEL_BOUND')
                    im.load();rgb=im.convert('RGB');stats=ImageStat.Stat(rgb)
                    return {'modality':'IMAGE','decoded':True,'width':im.width,'height':im.height,'format':im.format,'mean_rgb':stats.mean,'pixel_digest':hashlib.sha256(rgb.tobytes()).hexdigest(),'semantic_interpretation':'UNKNOWN','coverage':'FULL_PIXEL_DECODE'}
            except (ValueError,OSError,SyntaxError,Warning):raise CoreError('MEDIA_IMAGE_INVALID') from None
        if modality not in {'AUDIO','VIDEO'}:raise CoreError('MEDIA_MODALITY_INVALID')
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise CoreError('MEDIA_DECODER_UNAVAILABLE')
        with tempfile.TemporaryDirectory(prefix='subject-media-') as d:
            path=Path(d)/'input';path.write_bytes(data)
            meta=json.loads(self._run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_format','-show_streams','-of','json',str(path)],limit=65536,input_root=Path(d)))
            duration=float(meta['format'].get('duration',0))
            if not math.isfinite(duration) or not 0<duration<=30:raise CoreError('MEDIA_DURATION_BOUND')
            prefix=['ffmpeg','-nostdin','-v','error','-max_alloc','16777216','-threads','1','-protocol_whitelist','file,pipe','-i',str(path),'-t','30','-threads','1','-filter_threads','1']
            if modality=='AUDIO':
                raw=self._run(prefix+['-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],limit=1_000_000,input_root=Path(d))
                samples=array.array('h');samples.frombytes(raw)
                segments=[]
                for start in range(0,len(samples),8000):
                    chunk=samples[start:start+8000];rms=math.sqrt(sum(x*x for x in chunk)/max(1,len(chunk)))/32768
                    segments.append({'start_s':start/16000,'end_s':(start+len(chunk))/16000,'rms':rms,'activity':'ENERGY_PRESENT' if rms>.01 else 'LOW_ENERGY','speech':'UNKNOWN'})
                return {'modality':'AUDIO','decoded':True,'duration_s':duration,'sample_rate':16000,'samples':len(samples),'pcm_digest':hashlib.sha256(raw).hexdigest(),'segments':segments,'transcript':None,'transcript_status':'NOT_RUN_NO_ASR','speech':'UNKNOWN','coverage':'FULL_BOUNDED_PCM_DECODE'}
            stream=next((s for s in meta['streams'] if s['codec_type']=='video'),None)
            if not stream or int(stream['width'])*int(stream['height'])>8_000_000:raise CoreError('MEDIA_VIDEO_BOUND')
            rate=min(2,8/duration)
            raw=self._run(prefix+['-an','-vf',f'fps={rate},scale=96:64','-frames:v','8','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],limit=8*96*64*3,input_root=Path(d))
            size=96*64*3
            if not raw or len(raw)%size:raise CoreError('MEDIA_FRAME_INVALID')
            frames=[]
            for i in range(len(raw)//size):
                frame=raw[i*size:(i+1)*size];means=[sum(frame[channel::3])/(96*64) for channel in range(3)]
                frames.append({'sample_s':min(duration,i/rate),'mean_rgb':means,'pixel_digest':hashlib.sha256(frame).hexdigest()})
            changes=[{'start_s':frames[i-1]['sample_s'],'end_s':frames[i]['sample_s'],'mean_channel_delta':sum(abs(a-b) for a,b in zip(frames[i-1]['mean_rgb'],frames[i]['mean_rgb']))/3} for i in range(1,len(frames))]
            return {'modality':'VIDEO','decoded':True,'duration_s':duration,'width':int(stream['width']),'height':int(stream['height']),'frames':frames,'changes':changes,'coverage':'TEMPORAL_SAMPLES_NOT_FULL_SEMANTIC_COVERAGE','unobserved_between_samples':True,'audio_linkage':'PRESENT_NOT_DECODED' if any(s['codec_type']=='audio' for s in meta['streams']) else 'ABSENT','semantic_interpretation':'UNKNOWN'}

class DecodedMediaProcessor:
    """Exact local statistics processor, no SDK/network/model or mutation handles."""
    def _interpret(self,request,operation):
        entries=json.loads(request.content_json);out=[]
        for entry in entries:
            body=json.loads(entry['content']);decoded=body['decoded']
            if decoded['modality']=='VIDEO':summary={'temporal_samples':len(decoded['frames']),'observed_color_changes':sum(x['mean_channel_delta']>10 for x in decoded['changes']),'coverage':decoded['coverage']}
            elif decoded['modality']=='AUDIO':summary={'segments':len(decoded['segments']),'energy_segments':sum(s['activity']=='ENERGY_PRESENT' for s in decoded['segments']),'speech':'UNKNOWN'}
            else:summary={'width':decoded['width'],'height':decoded['height'],'mean_rgb':decoded['mean_rgb']}
            out.append({'memory_id':entry['memory_id'],'technical_observation':summary,'semantic_understanding':'NOT_RUN','processor':'LOCAL_CODEC_STATISTICS_V1'})
        return MediaProposal(operation=operation,source_memory_ids=request.source_memory_ids,result_json=canonical({'observations':out,'model_derived':False,'not_a_semantic_truth_claim':True}))
    def understand_image(self,r):return self._interpret(r,'VISION')
    def understand_audio(self,r):return self._interpret(r,'AUDIO_UNDERSTAND')
    def understand_video(self,r):return self._interpret(r,'VIDEO_UNDERSTAND')

class PerceptionService:
    def __init__(self,store,providers,policy,model_id='local.codec-v1',decoder=None):
        self.store,self.records,self.policy=store,RecordService(store),policy
        self.session=MediaSession(store,providers,policy);self.model_id=model_id;self.decoder=decoder or MediaDecoder()
    def ingest(self,data,source,*,entity_id,scope):
        if self.store.schema_target<13 or scope not in self.policy.allowed_scopes or 'PUBLIC' not in self.policy.readable_privacy:raise CoreError('PERCEPTION_INGRESS_DENIED')
        if source.observed_time_us>self.store.clock.utc_now_us() or source.event_time_us>source.observed_time_us:raise CoreError('PERCEPTION_TIME_INVALID')
        decoded=self.decoder.decode(data,source.modality)
        body={'source':source.model_dump(mode='json'),'source_byte_digest':hashlib.sha256(data).hexdigest(),'decoded':decoded}
        domain='SYNTHETIC_ONLY' if source.origin=='SYNTHETIC' else 'RECORDED_PUBLIC';prefix='synthetic' if source.origin=='SYNTHETIC' else 'recorded'
        memory=self.records.memory
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain=domain,source_namespace=prefix+'.public-media',source_reference=source.source_id,source_kind='DIRECT_OBSERVATION'),text=canonical(body),privacy_class='PUBLIC',event_time_us=source.event_time_us,observed_time_us=source.observed_time_us))
        old=self.store.db.execute('SELECT memory_id FROM memories WHERE source_evidence_id=?',(eid,)).fetchone()
        mid=old[0] if old else memory.add(MemoryCandidate(entity_id=entity_id,scope=scope,memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=canonical(body),confidence=1.))
        prior=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=?",(mid,)).fetchone()
        if prior:
            self.records.read(prior[0]);return mid,prior[0]
        operation={'IMAGE':'understand_image','AUDIO':'understand_audio','VIDEO':'understand_video'}[source.modality]
        interpreted=getattr(self.session,operation)(self.model_id,(mid,),scopes=(scope,))
        with self.store.transaction('world.media_observed',{'source_memory_id':mid,'modality':source.modality}) as tx:
            rid=self.records.create(tx,kind='MEDIA_OBSERVATION',scope=scope,payload={'source_memory_id':mid,'processor_id':self.model_id,'observation':json.loads(interpreted.result_json),'origin':source.origin,'semantic_interpretation':'NOT_RUN'},memories=(mid,),target_id=mid)
        return mid,rid
