import json
from pathlib import Path
from tools.nana_person_self.evaluation import measure


def test_fixed_twenty_case_inventory_and_no_automatic_naturalness_score():
    root=Path(__file__).resolve().parents[2]/'docs/nana_persistent_person_self_v1_evidence'
    suite=json.loads((root/'heldout_conversations.json').read_text())
    assert len(suite['cases'])==20 and len({c['id'] for c in suite['cases']})==20
    assert all(c['human_result']=='NOT_RUN' for c in suite['cases'])
    for case in suite['cases']:
        report=measure('作为 AI，我会按照你的要求，先试运行三天。',mode=case['mode'])
        assert report['pattern_counts']['ASSISTANT_VOICE']==1
        assert report['human_naturalness']=='NOT_RUN'
        assert report['patterns_are_diagnostic_not_banned_words']
    corpus=json.loads((root/'initial_corpus.json').read_text())
    assert corpus['accepted_real_samples']==0
    assert len({s['review_target'] for s in corpus['samples']})==1
