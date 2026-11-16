"""Compare upstream audio verdict with synthetic known tone and FLITE voice.

Requires FFmpeg with libflite and an upstream Python environment with NumPy.
Outputs classifications only; no transcript, external models, network or store.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from tools.nana_next_experience.experiments.video_audio_probe import measure


def run(command):
    return subprocess.run(command,stdin=subprocess.DEVNULL,check=True,timeout=120,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch',type=Path,required=True)
    parser.add_argument('--upstream-python',default=sys.executable);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nana-audio-compare-') as temp:
        root=Path(temp);audio_probe=args.watch.resolve()/'scripts/audio_probe.py';items={}
        fixtures={'tone':'sine=frequency=440:sample_rate=16000:duration=3',
                  'synthetic_voice':"flite=text='This is a short test of a synthetic voice':voice=slt"}
        for name,signal in fixtures.items():
            clip=root/(name+'.wav');out=root/(name+'.json')
            run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',signal,'-y',str(clip)])
            run([args.upstream_python,str(audio_probe),str(clip),'--json',str(out)])
            original=json.loads(out.read_text());measured=measure(clip)
            items[name]={'known_fixture':name,'original_verdict':original['verdict'],
                         'silence_measurement':measured}
        print(json.dumps({'fixture':'synthetic tone and synthetic FLITE speech',
            'upstream_audio_probe_commit':'8ca266f9cf9e5ffce7e9d424aa0e937a897b608d',
            'semantic_note':'one example each; audio classifier verdict is not ground truth',
            'model_calls':0,'results':items},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
