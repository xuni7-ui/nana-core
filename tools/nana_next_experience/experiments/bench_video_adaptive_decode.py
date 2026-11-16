"""Reproduce the small synthetic adaptive-vs-planned decode cost comparison."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

from tools.nana_next_experience.experiments.video_adaptive_decode import iter_windows
from tools.nana_next_experience.experiments.video_pts_decode import decode


def main():
    with tempfile.TemporaryDirectory() as directory:
        source=Path(directory)/'synthetic.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'testsrc2=s=32x32:r=30:d=60','-c:v','mpeg4','-g','60','-threads','1',
            '-y',str(source)],check=True,timeout=60)
        results=[]
        for mode in ('adaptive','planned','planned','adaptive'):
            started=time.perf_counter();digest=hashlib.sha256();ticks=[]
            if mode=='adaptive':
                stream=iter_windows('synthetic',source,0,60,width=32,height=32)
            else:
                stream=({'decoded':decode('synthetic',source,width=32,height=32,
                          start_seconds=a,end_seconds=b)} for a,b in ((0,30),(30,60)))
            attempts=2
            for item in stream:
                if 'decoded' in item:
                    frame=item['decoded'];ticks.extend(frame.pts_ticks);digest.update(frame.rgb24)
                else:
                    if not item['complete_requests']:raise RuntimeError('incomplete request')
                    attempts=item['attempts']
            results.append({'mode':mode,'wall_seconds':round(time.perf_counter()-started,6),
                'decode_attempts':attempts,'frames':len(ticks),'pts_ticks':ticks,
                'rgb_sha256':digest.hexdigest()})
        if any((r['pts_ticks'],r['rgb_sha256']) != (results[0]['pts_ticks'],results[0]['rgb_sha256'])
               for r in results[1:]):raise RuntimeError('output mismatch')
        for result in results:del result['pts_ticks']
        print(json.dumps({'synthetic':'60s 30fps 32x32 MPEG-4',
            'output_check':'identical integer PTS and decoded RGB hash',
            'model_calls':0,'token_cost':'not measured','cpu_memory':'not measured',
            'results':results},indent=2))


if __name__=='__main__':main()
