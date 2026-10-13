"""Offline qualification, metadata-only plan and future development E12 entry."""
import argparse
from pathlib import Path
import sys
from nana_core.contracts import CoreError
from nana_core.storage import canonical
from .contracts import RealCapturePlan
from .qualification import qualify
from .semantic import prepare,evaluate


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    q=sub.add_parser('qualify');q.add_argument('--output',required=True)
    e=sub.add_parser('e12');e.add_argument('--output',required=True);e.add_argument('--config')
    p=sub.add_parser('plan-template');p.add_argument('--output',required=True)
    try:
        args=parser.parse_args(argv)
        if args.command=='qualify':
            report=qualify(args.output)
            summary={k:report[k] for k in ('engineering_gate','E12','fixture_record_count','real_model_calls','physical_purge')}
            rc=0 if report['engineering_gate']=='PASS' else 1
        elif args.command=='e12':
            root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
            prepare(root/'snapshot')
            report=evaluate(root/'snapshot',root/'evaluation',args.config)
            summary={k:report[k] for k in ('E12','real_model_attempts','provider_models','phase_a_semantics','blockers')}
            rc=1 if report['E12']=='FAIL' else 0
        else:
            path=Path(args.output)
            with path.open('x') as f:
                f.write(RealCapturePlan(source_fingerprint='0'*64,record_kinds=('l1',),maximum_records=5).model_dump_json(indent=2)+'\n')
            summary={'kind':'REAL_CAPTURE_PLAN_ONLY','reader_enabled':False,'authorization_status':'NOT_RUN_REAL_DEPENDENCY'}
            rc=0
    except (CoreError,ValueError,OSError):
        print(canonical({'status':'READINESS_INPUT_OR_ENVIRONMENT_BLOCKED'}));return 2
    print(canonical(summary));return rc

if __name__=='__main__':sys.exit(main())
