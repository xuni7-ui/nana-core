from tools.nana_controlled_world.memory_scale import run

def test_bounded_context_important_old_corrected_withdrawn_and_corrupt(owned_root):
    result=run(owned_root/'scale',count=600)
    assert result['noise_events']==600 and result['candidate_count']<=128
    assert result['old_high_salience_selected'] and result['index_rebuild_stable'] and result['corruption_rejected']
