"""No production/private data; adversarial generated secret canaries stay private."""
import asyncio
import json
import os
from pathlib import Path
import pytest
from test_r041_bridge import fixture,ready
from test_r041_client import client_config_for_adversarial_test
from test_message_hook_adapter import FakeEvent
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
from src.plugins.astrbot_plugin_nana_shadow_observer.bridge_client import OneShotBridgeClient
from tools.nana_astrbot_shadow.one_shot_cli import main as receipt_cli
from tools.nana_astrbot_shadow.onboarding import main as onboarding_cli
from tools.nana_astrbot_shadow.bridge_cli import main as bridge_cli


def test_input_and_runtime_secret_canaries_never_reach_outputs(tmp_path,capsys):
    root,ipc,r,raw=fixture(tmp_path)
    raw.update(sender_id=raw['sender_id'])
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=1,trust=FixtureTrustStore())
        task,c=await ready(w);path,c=client_config_for_adversarial_test(ipc)
        notes=[]
        def logger(code):notes.append(code);raise RuntimeError('PRIVATE-SYNTHETIC-LOGGER-CANARY')
        client=OneShotBridgeClient(path,logger=logger)
        event=FakeEvent(platform=raw['platform'],sender=raw['sender_id'],umo=raw['conversation_id'],
            message_id=raw['event_id'],timestamp=raw['timestamp'])
        before=dict(vars(event));before_message=dict(vars(event.message_obj))
        assert await client.on_decorating_result(event) is None
        assert vars(event)==before and vars(event.message_obj)==before_message
        await client.close();w.stop_event.set();await task
        outputs=json.dumps(notes)+(ipc/'result.json').read_text()+(ipc/'session.json').read_text()
        for secret in (c['hash_key'],c['wire_key'],c['session_nonce'],raw['sender_id'],raw['conversation_id'],
            'PRIVATE-SYNTHETIC-LOGGER-CANARY'):
            assert secret not in outputs
    asyncio.run(run());captured=capsys.readouterr();assert captured.out==captured.err==''


def test_fixed_cli_diagnostics_never_echo_injected_body_or_secret(capsys,tmp_path):
    canary='PRIVATE-SYNTHETIC-BODY-AND-SESSION-CANARY'
    for cli,args in ((receipt_cli,['receipt','arm','--directory',str(tmp_path),'--force',canary]),
                     (onboarding_cli,['seal','--force',canary]),
                     (bridge_cli,['start','--ipc-directory',str(tmp_path),'--force',canary])):
        assert cli(args)==2
    captured=capsys.readouterr();assert canary not in captured.out+captured.err
    assert captured.err==''


def test_soak_driver_small_cycle_is_reproducible_automated_check(tmp_path):
    import r044_soak
    asyncio.run(r044_soak.cycle(tmp_path/'fixture',2))
    assert not any(p.name=='bridge.sock' or p.name=='client.json' for p in tmp_path.rglob('*'))
