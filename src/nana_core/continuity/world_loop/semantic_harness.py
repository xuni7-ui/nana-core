"""Explicit SYNTHETIC semantic oracle over actual pixels/PCM, not a live model.

Recognizes only dominant-color fields and audible periodic energy. It cannot
recognize people, general objects, speech, intent or arbitrary scene semantics.
"""
import array,base64,io,math,wave
from .semantic_contracts import SemanticDescriptor,MediaSemanticInput,MediaSemantics,SemanticObservation
from .cognition import StructuredProposal
from .harness import propose_from_context,provider_harness
from contextlib import contextmanager

def semantic_proposer(request):
    if request.cognitive_role!='MEDIA':
        # Focus the synthetic interpreter on newly supplied observations; other
        # context is background knowledge, not another independent opportunity.
        if request.primary_source_refs:
            import json
            from ...storage import canonical
            package=json.loads(request.context_json)
            package['blocks']=[b for b in package['blocks'] if b['kind']!='MEMORY' or set(b['source_memory_ids'])&set(request.primary_source_refs)]
            request=request.model_copy(update={'context_json':canonical(package)})
        return propose_from_context(request)
    from PIL import Image,ImageStat
    from ...storage import canonical
    inp=MediaSemanticInput.model_validate_json(canonical(request.role_input));observations=[]
    for i,p in enumerate(inp.parts):
        raw=base64.b64decode(p.data_b64)
        if p.kind=='IMAGE':
            with Image.open(io.BytesIO(raw)) as image:
                mean=ImageStat.Stat(image.convert('RGB')).mean
            names=('red','green','blue');label=names[max(range(3),key=lambda k:mean[k])]+'-dominant field'
            if max(mean)-min(mean)<15:label='neutral field'
            observations.append(SemanticObservation(kind='ATTRIBUTE',part_indices=(i,),label=label,start_s=p.start_s,end_s=p.end_s,confidence=.6,uncertainty='RELEVANT'))
        else:
            with wave.open(io.BytesIO(raw),'rb') as audio:pcm=audio.readframes(audio.getnframes());rate=audio.getframerate()
            samples=array.array('h');samples.frombytes(pcm)
            rms=math.sqrt(sum(x*x for x in samples)/max(1,len(samples)))
            crossings=sum(a<=0<b for a,b in zip(samples,samples[1:]));hz=crossings*rate/max(1,len(samples))
            label='low-energy signal' if rms<100 else 'high periodic tone' if hz>=500 else 'low periodic tone'
            observations.append(SemanticObservation(kind='ACOUSTIC_EVENT',part_indices=(i,),label=label,start_s=p.start_s,end_s=p.end_s,confidence=.55,uncertainty='HIGH'))
    if inp.modality=='VIDEO':
        observations.append(SemanticObservation(kind='SUMMARY',part_indices=tuple(range(len(inp.parts))),label='Sampled fields: '+', '.join(dict.fromkeys(o.label for o in observations)),start_s=0,end_s=inp.duration_s,derived_from=tuple(range(len(observations))),confidence=.4,uncertainty='HIGH'))
    return StructuredProposal(interpretation='Synthetic narrow pixel/PCM oracle; not general media understanding',source_refs=(inp.source_memory_id,),media=MediaSemantics(source_memory_id=inp.source_memory_id,source_byte_digest=inp.source_byte_digest,observations=tuple(observations),coverage='WHOLE_IMAGE' if inp.modality=='IMAGE' else 'EXPLICIT_SEGMENTS',asr_status='NOT_SUPPORTED'),uncertainty='HIGH',confidence=.4)

@contextmanager
def semantic_harness(*,proposer=semantic_proposer,mode='ok',delay=0):
    with provider_harness(proposer,mode=mode,delay=delay) as (transport,metrics):
        transport.semantic_descriptor=SemanticDescriptor(provider_id=transport.provider_id,model_id=transport.model_id,modalities=('IMAGE','AUDIO','VIDEO'),max_input_bytes=98304)
        yield transport,metrics
