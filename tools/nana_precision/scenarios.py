"""Representative baseline coverage using existing independently asserted tests.

Not twenty new subsystems or a replacement oracle. Same selectors run on the
exact old source and candidate. Each scope is retained; simulated UI != device.
"""
import argparse,json,subprocess,sys
from pathlib import Path

CASES = {
    'simple_explicit': 'tests/open_autonomy/test_planning.py::test_plan_proposals_do_not_invent_capability_or_satisfy_missing_conditions',
    'multistep_files': 'tests/controlled_hands/test_application.py::test_real_subject_outcome_learning_transfer_and_bounded_extension',
    'document_code_research': 'tests/controlled_world/test_sources_research.py::test_expired_world_history_does_not_permanently_hide_current_belief',
    'multigoal_dependencies': 'tests/open_autonomy/test_planning.py::test_subgoal_dependency_suspend_resume_and_completed_cause_dedup',
    'goal_change': 'tests/controlled_world/test_project_presence.py::test_supersession_only_links_original_c_withdrawal_and_adoption',
    'source_disappears': 'tests/open_life/test_runtime_intake.py::test_configured_source_runs_in_original_idle_runtime_and_withdraws',
    'stale_environment': 'tests/controlled_world/test_lab_browser.py::test_stale_dom_revision_cannot_become_current_observation',
    'tool_failure': 'tests/controlled_hands/test_recovery.py::test_real_file_ipc_disagreement_remains_unknown_without_retry',
    'partial_effect': 'tests/controlled_world/test_lab_browser.py::test_owned_task_api_cru_duplicate_collision_partial_and_drop',
    'unknown': 'tests/controlled_world/test_failures_ingress.py::test_real_http_drop_plus_verifier_socket_unavailable_unknown_no_resend',
    'crash_recovery': 'tests/open_life/test_recovery.py::test_actual_sigkill_after_c_commit_before_attention_ack',
    'model_swap': 'tests/controlled_world/test_model_resource.py::test_wording_latency_model_swap_and_malformed_same_subject',
    'new_task_type': 'tests/world_loop/test_living.py::test_dynamic_sourced_goals_and_two_self_detected_skill_kinds',
    'negative_transfer': 'tests/controlled_world/test_noisy_growth.py::test_actual_noisy_heldout_failure_revised_problem_transfer_and_counterexample',
    'correction': 'tests/world_loop/test_foundation.py::test_world_temporal_conflict_correction_and_no_resurrection',
    'casual_talk': 'tests/vision_first/test_context_fit.py::test_vent_help_share_unclear_and_busy_are_semantic_proposals_not_tasks',
    'self_opportunity': 'tests/open_life/test_attention_research.py::test_queue_original_c_restart_idempotency_and_suppression',
    'rest_conflict': 'tests/open_life/test_attention_research.py::test_load_and_expensive_learning_allow_rest',
    'mobile_ui_simulation': 'tests/open_life/test_embodied.py::test_simulator_gestures_compile_only_not_authority',
    'browser_state_task': 'tests/controlled_world/test_lab_browser.py::test_five_process_lab_timer_and_structural_navigation',
}


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('FRESH_RECEIPT_ROOT_REQUIRED')
    a.out.mkdir(parents=True)
    xml=a.out/'results.xml'
    with (a.out/'pytest.txt').open('w') as log:
        result=subprocess.run([sys.executable,'-m','pytest','-q',*dict.fromkeys(CASES.values()),'--junitxml='+str(xml)],cwd=a.source,stdout=log,stderr=subprocess.STDOUT)
    pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip()
    receipt={'source_commit':pin,'exit_code':result.returncode,'cases':CASES,'scope':'REPRESENTATIVE_EXISTING_CORE_ASSERTIONS_OWNED_DEV_OR_FIXTURE','real_models':False,'limitations':['Document/code research row is temporal-source representative coverage, not large-document semantic comprehension.','Mobile UI is compile-only simulation, not real device control.','No LLM/tools ablation; no human naturalness.'],'raw_xml':str(xml)}
    (a.out/'coverage.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'exit_code':result.returncode,'categories':len(CASES),'source_commit':pin}))
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
