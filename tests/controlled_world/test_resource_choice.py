import pytest
from nana_core.continuity.open_life.opportunities import ActivityCost,OpportunityQueue
from nana_core.continuity.world_loop.reference import open_runtime,capture
from nana_core.continuity.records import RecordService
from nana_core.presence.authority import VirtualClock
from tests.open_life.test_attention_research import candidate,judge


@pytest.mark.parametrize('cost',[
    {'compute':'HEAVY'},{'time':'LONG'},{'external':'REQUIRES_RESERVATION'},
    {'external':'UNKNOWN'},{'storage':'LARGE'},{'interruption':'HEAVY'},
])
def test_c_can_choose_cheaper_then_rest_without_magic_authority(owned_root,cost):
    with open_runtime(owned_root/'self.db',VirtualClock()) as r:
        q=OpportunityQueue(r);expensive=capture(r,'expensive',{'known_gap':True});cheap=capture(r,'cheap',{'local_alternative':True})
        first=q.offer(candidate(r,expensive,resource_estimate=ActivityCost(**cost)))
        second=q.offer(candidate(r,cheap,resource_estimate=ActivityCost()))
        selected=q.opportunity();assert selected['opportunity_id']==second
        cheaper=judge(r,q,second);assert cheaper['behavior']=='EXPLORE'
        costly=judge(r,q,first);assert costly['behavior'] in {'REST','DEFER','WATCH','STAY_SILENT','DO_NOTHING'}
        body=RecordService(r.store).read(r.store.one('jobs',first)['record_id'])['payload']
        assert body['candidate']['resource_estimate']['basis']=='HOST_STRUCTURAL_ESTIMATE'
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
