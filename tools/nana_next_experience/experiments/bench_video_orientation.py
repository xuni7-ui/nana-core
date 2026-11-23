"""Paired synthetic FFmpeg orientation cost; no model, account, or token billing."""
import json
from pathlib import Path
import resource
import statistics
import subprocess
import tempfile
import time

from PIL import Image,ImageChops,ImageStat
from tools.nana_next_experience.experiments.video_pts_decode import decode


def main():
    with tempfile.TemporaryDirectory(prefix='nana-orientation-bench-') as root:
        source=Path(root)/'source.mp4';tagged=Path(root)/'rotation.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'testsrc2=s=320x180:r=10:d=15','-c:v','mpeg4','-threads','1','-y',str(source)],check=True,timeout=30)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-display_rotation','90','-i',str(source),
            '-c','copy','-y',str(tagged)],check=True,timeout=30)
        samples={'raw':[],'display':[]};cpus={'raw':[],'display':[]};results={}
        for i in range(3):
            for mode in (('raw','display') if i%2==0 else ('display','raw')):
                before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
                result=decode('synthetic.rotation.benchmark',tagged,width=160 if mode=='raw' else 90,
                              height=90 if mode=='raw' else 160,orientation=mode)
                samples[mode].append(time.perf_counter()-start);after=resource.getrusage(resource.RUSAGE_CHILDREN)
                cpus[mode].append(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime);results[mode]=result
        raw,display=results['raw'],results['display'];size=160*90*3;diff=[];exact=0;maximum=0
        if raw.pts_ticks!=display.pts_ticks:raise RuntimeError('PTS differs between modes')
        for i in range(len(raw.timestamps)):
            a=Image.frombytes('RGB',(160,90),raw.rgb24[i*size:(i+1)*size]).transpose(Image.Transpose.ROTATE_90)
            b=Image.frombytes('RGB',(90,160),display.rgb24[i*size:(i+1)*size])
            d=ImageChops.difference(a,b);diff.append(statistics.mean(ImageStat.Stat(d).mean))
            maximum=max(maximum,max(x[1] for x in d.getextrema()));exact+=a.tobytes()==b.tobytes()
        print(json.dumps({'frames':len(diff),'source_bytes':tagged.stat().st_size,'pts_equal':True,'pixel_exact_frames':exact,
            'mean_absolute_rgb_difference':statistics.mean(diff),'max_channel_difference':maximum,
            'wall_seconds':samples,'wall_median_seconds':{k:statistics.median(v) for k,v in samples.items()},
            'ffmpeg_ffprobe_child_cpu_seconds':cpus,'peak_memory':'NOT_MEASURED',
            'scope':'synthetic 15s source, 3 paired runs; raw scaled then rotated vs autorotated then scaled; no model, Token, bill or semantic quality'},indent=2))


if __name__=='__main__':main()
