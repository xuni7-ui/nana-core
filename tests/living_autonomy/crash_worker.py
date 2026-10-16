"""Single dangerous cut: fixture effect durable, Kernel receipt not committed."""
import os,signal,sys
from pathlib import Path
from .helpers import fresh
from .test_agency import setup,start

def main():
    root=Path(sys.argv[1]);path=root/'subject'/'self.db';world=root/'world'/'effect.fixture.json'
    with fresh(path) as r:
        _,mid=setup(r,world);start(r,mid)
        port=r.work.agency.realization.kernel.capability;original=port.execute
        def effect_then_die(inv):
            result=original(inv)
            os.kill(os.getpid(),signal.SIGKILL)
            return result
        port.execute=effect_then_die
        r.step()
if __name__=='__main__':main()
