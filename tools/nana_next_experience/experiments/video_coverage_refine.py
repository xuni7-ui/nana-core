"""Optional experimental change-aware swaps within an explicit gap allowance."""
from tools.nana_next_experience.experiments.video_coverage import plan


def refine(duration, candidates, budget, *, max_gap):
    """Retain coverage priority while trading redundant samples for changes.

    Scores are observable frame-change signals, never semantic importance.
    The maximum gap cannot grow above the requested target, unless the initial
    candidate set already cannot achieve it; then it cannot grow at all.
    """
    candidates=tuple(candidates)
    initial=plan(duration,candidates,budget,max_gap=max_gap)
    selected=list(initial['timestamps'])
    by_time={candidate.seconds:candidate for candidate in candidates}
    def score(timestamp):
        item=by_time[timestamp]
        return max(item.cut,item.motion)
    def gap(times):
        points=[0,*sorted(times),duration]
        return max(b-a for a,b in zip(points,points[1:]))
    gap_limit=max(max_gap,gap(selected))
    swaps=0
    # The highest 64 signals bound CPU cost for long candidate lists.
    for candidate in sorted(candidates,key=lambda c:(-max(c.cut,c.motion),c.seconds))[:64]:
        if candidate.seconds in selected: continue
        options=[]
        for index,old in enumerate(selected):
            if score(candidate.seconds)<=score(old): continue
            trial=selected.copy();trial[index]=candidate.seconds
            trial_gap=gap(trial)
            if trial_gap<=gap_limit:
                options.append((score(old),trial_gap,old,index))
        if options:
            _,_,_,index=min(options)
            selected[index]=candidate.seconds;swaps+=1
    times=tuple(sorted(selected));points=(0.0,*times,duration)
    gaps=tuple((a,b) for a,b in zip(points,points[1:]) if b-a>max_gap)
    return {'timestamps':times,'gaps':gaps,'max_gap_target':max_gap,
            'coverage_target_met':not gaps,'change_swaps':swaps,
            'meaning':'sampling only; change scores do not establish importance'}


def main():
    import argparse
    import json
    from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
    parser=argparse.ArgumentParser();parser.add_argument('media')
    parser.add_argument('--budget',type=int,default=4)
    parser.add_argument('--max-gap',type=float,required=True)
    args=parser.parse_args();measured=probe(args.media)
    result=refine(measured['duration'],measured['candidates'],args.budget,max_gap=args.max_gap)
    print(json.dumps({'scan_complete':measured['scan_complete'],'selection':result},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
