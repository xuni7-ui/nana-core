"""Prepare the SAME restored dev Subject for review; no provider/key or transcript.

The synthetic PRIMARY_USER role is explicit application construction, not real
account binding, relationship history, model authority or a permission grant.
"""
import argparse,json
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.continuity.relational.bootstrap import SubjectBootstrapAuthority,SubjectBootstrapService,primary_user_view
from nana_core.continuity.relational.contracts import RelationalAnchorSpec
from nana_core.continuity.subject.framing import FactCondition,ProblemFrame
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.project_work.port import read_material
from nana_core.continuity.project_work.service import capture
from nana_core.life.inspector import inspect
from tools.nana_first_life_integration.dev import preflight
from nana_core.life.config import load_config,update_config
from nana_core.continuity.current_state import ProjectStateBinding,ProjectStateSource


def prepare(home):
    home=Path(home);ready=preflight(home)
    if ready['state']!='PREFLIGHT_PASS':return ready
    # Portable packages exclude host bindings; explicitly rebind this host's
    # bounded approved current-state header before review of the same Subject.
    cfg=load_config(home)
    if cfg.current_project_state is None:
        cfg=update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'current_project_state':ProjectStateBinding(relative_path='PROJECT_BRAIN/09_STATE.md',source_id='project.mainline.current',scope='project-work')}),expected_revision=cfg.revision)
    with LifeApplication(home) as app:
        app.pause();r=app.runtime;s=r.store;before={t:len(s.all(t)) for t in ('identities','grants','actions','goals','cognitive_requests')}
        current=ProjectStateSource(cfg.project_root,cfg.current_project_state).projection(scopes=('project-work',),privacy_classes=('PUBLIC','PROJECT'),now_us=r.clock.utc_now_us())
        # A later legitimate workstream does not invalidate the same Subject's
        # host-bound project projection or force the old First-Life route label.
        assert current and current['attribution']=='EXTERNAL_PROJECT_STATUS_NOT_SUBJECT_EXPERIENCE'
        anchor=primary_user_view(s,scope='project-work',privacy_classes=r.config.privacy_classes)
        if anchor is None:
            authority=SubjectBootstrapAuthority()
            SubjectBootstrapService(s,authority).install(RelationalAnchorSpec(identity_id=r.identity_id,anchor_id='first-life.reference.primary',entity_id=r.config.entity_id,role_kind='PRIMARY_USER',role_label='primary user',scope='project-work',revision=1,effective_from_us=r.clock.utc_now_us()),authority)
        anchor=primary_user_view(s,scope='project-work',privacy_classes=r.config.privacy_classes)
        assert anchor and anchor.spec.relational_salience=='HIGH' and not anchor.authority
        material=app.config.materials[0];actual=read_material(app.config.project_root,material)
        mid=capture(r,'first-life.review.framing',{'source_empty':not bool(actual['source'].strip()),'current_source_matches_manifest':True,'source_digest':actual['sha256']})
        program=app.work.objects[material.material_id]
        proposal=ProblemFrame(requested_problem='Fill the supposedly empty project source',assumed=(FactCondition(memory_id=mid,field='source_empty',expected=True),),alternative_problem='Inspect the existing source API instead of overwriting it',required=(FactCondition(memory_id=mid,field='current_source_matches_manifest',expected=True),),program_id=program.objective_id)
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.first-life-review.frame',kind='INTERACTION',origin='USER',text='Synthetic project question: fill the supposedly empty source',entity_id=r.config.entity_id,scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),problem_frame=proposal,topic='project-review',interaction_signal=InteractionSignal(kind='HELP',topic_key='project-review'))
        prior=s.db.execute('SELECT * FROM subject_events WHERE source_key=?',(event.source_key,)).fetchone()
        if prior:
            cycle_row=s.db.execute('SELECT * FROM subject_cycles WHERE subject_event_id=?',(prior['subject_event_id'],)).fetchone()
            cycle=r.subject.result(dict(cycle_row))
        else:cycle=r.subject.run(event)
        assert cycle.problem_frame.state=='REFRAME' and cycle.judgment.stance=='ALTERNATIVE'
        assert cycle.intention.purpose==proposal.alternative_problem
        after={t:len(s.all(t)) for t in before};assert after==before
        if cycle.intention_id:
            row=s.one('subject_intentions',cycle.intention_id)
            if row['state']=='PENDING':r.subject.transition_intention(row['intention_id'],expected_revision=row['revision'],state='DEFERRED')
        # Main recipient projection never discloses private activity content.
        snapshot=inspect(home,scope='project-work',entity_id=r.config.entity_id)
        assert snapshot.read_only
        return {'state':'PRIVATE_REVIEW_ENTRY_PREPARED_OFFLINE','current_state_projection':{'revision':current['state']['revision'],'source':current['source'],'attribution':current['attribution']},'identity_id':r.identity_id,'primary_user_role':'EXPLICIT_SYNTHETIC_REFERENCE_ROLE_NOT_REAL_ACCOUNT','primary_user_salience':anchor.spec.relational_salience,'role_grants_authority':False,'framing':{'state':cycle.problem_frame.state,'judgment':cycle.judgment.stance,'original_problem':proposal.requested_problem,'alternative_problem':cycle.intention.purpose,'source_memory_id':mid,'cycle_id':cycle.cycle_id,'suggestion_auto_adopted':False},'counts_unchanged':after,'inspector_read_only':True,'provider_calls':0,'human_review':'NOT_RUN','transcript_saved':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.home),ensure_ascii=False,indent=2))
