from tools.nana_first_life.rehearsal import run
from tests.cloud_life.conftest import REPO


def test_actual_process_owner_handoff_and_fresh_lineage_rollback(tmp_path):
 result=run(REPO,tmp_path/'rehearsal')
 assert result['same_identity'] and result['old_writer_resume_rejected']
 assert result['active_owner_transfer_rejected'] and result['recent_continuity_survives']
 assert len(set(result['all_owned_pids']))==3 and result['epochs']==sorted(set(result['epochs']))
 assert result['real_social_sends']==0 and not result['production_cutover']
