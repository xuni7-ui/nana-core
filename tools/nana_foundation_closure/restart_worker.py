"""Qualification-only child: commit a sourced self-wake, then await test SIGKILL."""
import argparse,json,signal
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.continuity.subject import SubjectInput


def run(home,mid,marker):
    with LifeApplication(home,bootstrap_grant=False) as app:
        app.pause();r=app.runtime
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.need.crash-reselection',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class='PROJECT',source_memory_ids=(mid,),task_class='owned-document')
        c=r.subject.run(event)
        marker.write_text(json.dumps({'event':event.model_dump(mode='json'),'cycle_id':c.cycle_id,'identity_id':r.identity_id,'state':c.experience_need.state,'behavior':c.intention.behavior,'actions':len(r.store.all('actions'))}))
        signal.pause()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);p.add_argument('--mid',required=True);p.add_argument('--marker',type=Path,required=True);a=p.parse_args();run(a.home,a.mid,a.marker)
