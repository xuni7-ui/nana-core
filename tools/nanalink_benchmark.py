"""Finite infrastructure measurement; no account, model or social send.

Report bytes as bytes, CPU as CPU. This is NOT an effective-cognition quality,
real-provider token reduction or real-account throughput qualification.
"""
import asyncio
import json
import resource
import tempfile
import time
from pathlib import Path
from nana_core.nanalink.contracts import Account, Event, OperationReceipt, Outcome
from nana_core.nanalink.transport import EventTransport
from nana_core.nanalink.media import MediaCache


async def measure():
    queue=EventTransport(capacity=64,per_account=16,dedupe=512)
    account=Account(platform='qq',adapter_id='qq.onebot',account_id='42')
    started, cpu=time.perf_counter(),time.process_time()
    async def review(event):
        return OperationReceipt(operation_id=event.key,outcome=Outcome.UNKNOWN,reason='METADATA_BENCHMARK_NO_COGNITION')
    for i in range(2000):
        event=Event(account=account,event_id=str(i),kind='message.created',message_id=str(i),
                    conversation_kind='private',conversation_id='43',sender_id='43',observed_at_us=i,
                    privacy='PROJECT',origin='SYNTHETIC_LOOPBACK',raw_sha256='a'*64,raw_reference='onebot:'+str(i))
        assert queue.offer(event)=='QUEUED'
        assert queue.offer(event)=='DUPLICATE'
        await queue.drain_once(review)
    elapsed=time.perf_counter()-started
    spent=time.process_time()-cpu
    with tempfile.TemporaryDirectory(prefix='nanalink-bench-') as root:
        cache=MediaCache(Path(root)/'media',source_current=lambda ref:ref=='fixture',max_bytes=16*1024*1024,item_bytes=8*1024*1024)
        chunk=b'x'*65536
        handle=cache.put((chunk for _ in range(128)),source_ref='fixture')
        duplicate=cache.put((chunk for _ in range(128)),source_ref='fixture')
        assert handle.sha256==duplicate.sha256 and cache.total==8*1024*1024
        media=dict(cache.metrics,retained_bytes=cache.total,range_bytes=len(cache.read(handle)))
        cache.close()
    return {'scope':'SYNTHETIC_INFRASTRUCTURE_ONLY','events':dict(queue.metrics),
        'elapsed_seconds':elapsed,'cpu_seconds':spent,'cpu_ms_per_admitted_event':spent/2,
        'peak_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'queue_capacity':queue.capacity,'per_account_capacity':queue.per_account,'dedupe_capacity':queue.dedupe,
        'dedupe_retained':len(queue.seen),'media':media,'model_calls':0,'provider_tokens':0,
        'external_requests':0,'real_social_sends':0,'effective_cognition_cost':'NOT_QUALIFIED_NO_REAL_PROVIDER'}


if __name__=='__main__':
    print(json.dumps(asyncio.run(measure()),indent=2))
