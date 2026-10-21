"""Memory-only exact final leak check; never dispatches a Provider request."""
import argparse,json
from pathlib import Path
from .live_review import secret_from_terminal,scan_and_save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();resolver=secret_from_terminal()
    try:
        result={'purpose':'FINAL_EXACT_LEAK_AUDIT_ONLY','provider_calls':0}
        scan_and_save(a.home,a.output,result,resolver)
        print(json.dumps(result),flush=True)
    finally:resolver.clear()

if __name__=='__main__':main()
