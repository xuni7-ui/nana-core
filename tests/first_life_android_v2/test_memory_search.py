"""Authoritative read-only search beyond the recent display window."""
from nana_core.life.application import LifeApplication
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from .test_http_integration import running, http, login, base


def test_actual_chinese_search_outside_recent_window_and_withdrawal(running):
    server, service = running
    service.supervisor.stop()
    with LifeApplication(service.supervisor.home) as app:
        app.pause()
        memory = MemoryService(app.runtime.store)
        memory.entity('other-person', 'PERSON')
        def add(key, text, entity='project-user', privacy='PROJECT'):
            evidence = memory.capture(EvidenceInput(provenance=Provenance(
                source_namespace='synthetic.memory-search', source_reference=key, source_kind='DIRECT_OBSERVATION'),
                text=text, privacy_class=privacy, observed_time_us=app.runtime.clock.utc_now_us()))
            return memory.add(MemoryCandidate(entity_id=entity, scope='project-work',
                memory_type=MemoryType.EPISODIC, epistemic_kind='OBSERVATION', source_evidence_id=evidence, text=text))
        old = add('old', 'SYNTHETIC 昨天我们一起整理了星图，这是共同项目备注')
        for n in range(40): add('recent-'+str(n), 'SYNTHETIC unrelated recent note '+str(n))
        add('foreign', 'SYNTHETIC 一起整理了星图 OTHER_PERSON', entity='other-person')
        add('private', 'SYNTHETIC 一起整理了星图 PRIVATE_WITHHELD', privacy='PERSONAL')
    service.supervisor.start()
    headers = login(server, service)
    visible = http(server, 'views/memories', headers=headers)[1]['data']['memories']
    assert old not in {m['memory_id'] for m in visible} and len(visible)==32
    assert http(server, 'memories/search', 'POST', {'query':'整理了星图'})[0] in {401,403}
    revision = service.ledger.revision
    code, result, _ = http(server, 'memories/search', 'POST', {'query':'整理了星图'}, headers)
    assert code==200 and service.ledger.revision==revision
    assert [m['memory_id'] for m in result['data']['memories']]==[old]
    assert result['data']['coverage']=='LITERAL_TEXT_MATCH_NOT_SEMANTIC'
    assert 'PRIVATE_WITHHELD' not in str(result) and 'OTHER_PERSON' not in str(result)
    assert http(server, 'memories/search', 'POST', {'query':'%_not_a_wildcard'}, headers)[1]['data']['memories']==[]
    withdrawn = http(server, 'commands', 'POST', {**base(service,'withdraw-old-search'),
        'operation':'WITHDRAW', 'target_id':old}, headers)
    assert withdrawn[0]==200 and withdrawn[1]['data']['state']=='VERIFIED'
    assert http(server, 'memories/search', 'POST', {'query':'整理了星图'}, headers)[1]['data']['memories']==[]
    service.supervisor.stop(); service.supervisor.start()
    assert http(server, 'memories/search', 'POST', {'query':'整理了星图'}, headers)[1]['data']['memories']==[]
