"""Generated, non-personal actual codec samples. No downloads or private files."""
import io,math,struct,subprocess,wave,tempfile
from pathlib import Path

def media_samples(variant=0):
    from PIL import Image
    image=Image.new('RGB',(48,32),(20+variant*30,80,160));out=io.BytesIO();image.save(out,format='PNG')
    audio=io.BytesIO()
    with wave.open(audio,'wb') as w:
        w.setparams((1,2,16000,0,'NONE','not compressed'))
        w.writeframes(b''.join(struct.pack('<h',int(9000*math.sin(2*math.pi*(440+variant*110)*i/16000))) for i in range(16000)))
    with tempfile.TemporaryDirectory(prefix='public-media-sample-') as d:
        p=Path(d)/'clip.mp4'
        cmd=['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','testsrc2=size=96x64:rate=4','-t','2','-c:v','mpeg4','-threads','1','-y',str(p)]
        subprocess.run(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)
        video=p.read_bytes()
    return {'IMAGE':out.getvalue(),'AUDIO':audio.getvalue(),'VIDEO':video}
