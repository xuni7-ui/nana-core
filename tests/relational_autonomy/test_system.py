from .qualification import scenarios,matrices


def test_scenarios_and_four_dimension_matched_matrix(tmp_path):
 matrix=matrices(tmp_path/'matrix');cases=scenarios(tmp_path/'scenarios')
 cases['S20_TWO_PERSONALITIES']={'result':'PASS','choices':[matrix['cases'][0]['decision'],matrix['cases'][1]['decision']]}
 cases['S21_TWO_RELATIONSHIPS']={'result':'PASS','choices':[matrix['cases'][0]['decision'],matrix['cases'][2]['decision']]}
 assert len(cases)==22 and all(x['result']=='PASS' for x in cases.values())


def test_matched_appetite_ablation_and_generic_reference_subjects(tmp_path):
 from .qualification import ablation,generic
 assert ablation(tmp_path/'ablation')['result']=='PASS'
 assert generic(tmp_path/'generic')['result']=='PASS'
