from .life import cases,generic,soak

def test_single_subject_scenario_matrix_and_generic_framework(tmp_path):
 matrix=cases(tmp_path/'matrix');subjects=generic(tmp_path/'generic')
 matrix['S6_RELATIONSHIP_HIGH']={'result':subjects['result'],'authority_not_expanded':subjects['authority_not_expanded']}
 assert len(matrix)==15 and all(x['result']=='PASS' for x in matrix.values())


def test_sixty_virtual_day_hot_state_is_bounded(tmp_path):
 report=soak(tmp_path/'soak')
 assert report['result']=='PASS' and report['virtual_days']==60
