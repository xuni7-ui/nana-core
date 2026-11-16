"""Synthetic baseline vs indexed timing overlap; no transcript/model/network."""
import argparse
import json
import time
from tools.nana_next_experience.experiments.video_caption_acoustic import review


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=3000)
    n=parser.parse_args().count
    if not 1<=n<=3000:raise ValueError('benchmark bound')
    intervals=[(i*.2,i*.2+.1) for i in range(n)]
    cues=[{'cue_id':str(i),'source_id':'src','start':i*.2+.03,'end':i*.2+.17} for i in range(n)]
    start=time.perf_counter()
    expected=[sum(max(0,min(c['end'],b)-max(c['start'],a)) for a,b in intervals)/(c['end']-c['start']) for c in cues]
    baseline=time.perf_counter()-start
    start=time.perf_counter()
    result=review(cues,{'state':'MEASURED','duration':600,'measured_intervals':[(0,600)],'silence_intervals':intervals},
                  acoustic_source_id='src',timeline_aligned=True)
    indexed=time.perf_counter()-start
    max_difference=max(abs(a-b['silence_overlap_fraction']) for a,b in zip(expected,result))
    assert max_difference<1e-9
    print(json.dumps({'synthetic_cues':n,'synthetic_intervals':n,'baseline_s':baseline,
        'indexed_s':indexed,'max_absolute_fraction_difference':max_difference,
        'baseline_scope':'overlap only','indexed_scope':'validation and overlap and output',
        'model_calls':0,'token_measurement':'NOT_MEASURED'},indent=2))


if __name__=='__main__':main()
