"""Fixed fixture worker. No Store, authority, tools, credentials or network API."""
import json
import sys
import time
from ..continuity.cognition import FrozenModelInput,AnalyticalFixturePort,CautiousFixturePort


def main():
    try:
        if len(sys.argv)!=2 or sys.argv[1] not in {'analytical','cautious','timeout','unavailable'}:raise ValueError()
        raw=sys.stdin.buffer.read(196609)
        if len(raw)>196608:raise ValueError()
        request=FrozenModelInput.model_validate_json(raw)
        kind=sys.argv[1]
        if kind=='timeout':time.sleep(60)
        if kind=='unavailable':raise ValueError()
        model=AnalyticalFixturePort() if kind=='analytical' else CautiousFixturePort()
        result=json.dumps({'proposal':model.propose(request)}).encode()
        if len(result)>32768:raise ValueError()
        sys.stdout.buffer.write(result)
    except Exception:
        # No exception text, request body, repr or credential reflection.
        raise SystemExit(2) from None

if __name__=='__main__':main()
