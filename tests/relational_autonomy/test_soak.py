from .soak import run


def test_ninety_virtual_day_mixed_relationship_life(tmp_path):
 result=run(tmp_path/'life')
 assert result['virtual_days']==90 and result['result']=='PASS'
