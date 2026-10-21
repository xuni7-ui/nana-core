"""Private, bounded entry into the original First-Life Runtime (no new loop).

Credentials are explicitly supplied through a memory FD or echo-disabled terminal.
Only sanitized operational metadata is retained; conversation wording is volatile.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from nana_core.contracts import CoreError
from nana_core.life.config import load_config
from nana_core.life.provider import configured_router
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from tools.nana_first_life_integration.dev import preflight
from tools.nana_first_life_integration.live_review import secret_from_terminal, scan_and_save
from .attempt import HOME, IDENTITY, resolver_from_fd


def start(home, seconds, output, resolver):
    if Path(home) != HOME or not 0 < seconds <= 7200:
        raise CoreError('QUALIFICATION_SCOPE_DENIED')
    if Path(output).exists():
        raise CoreError('QUALIFICATION_OUTPUT_EXISTS_NO_REPLAY')
    ready = preflight(home, live=True, resolver=resolver)
    if ready['state'] != 'PREFLIGHT_PASS' or ready['identity_id'] != IDENTITY:
        raise CoreError('QUALIFICATION_PREFLIGHT_BLOCKED')
    cfg = load_config(home)
    if cfg.provider_timeout_ms > 15000 or set(cfg.remote_privacy) - {'PUBLIC', 'PROJECT'}:
        raise CoreError('QUALIFICATION_POLICY_DENIED')
    calls = []
    report = {'identity_id': IDENTITY, 'calls': calls, 'retry': 0, 'fallback': 0,
              'human_review': 'NOT_RUN', 'actual_billing': 'UNKNOWN',
              'transcript_saved': False, 'status': 'STARTING_ORIGINAL_RUNTIME'}
    original = OpenAIJSONTransport.exchange

    def observed(port, request):
        u = urlsplit(port.endpoint)
        if (u.scheme != 'https' or u.hostname != 'api.deepseek.com' or u.port is not None
                or u.path not in {'/chat/completions', '/v1/chat/completions'}
                or u.query or u.fragment or u.username or port.model_id != 'deepseek-flash'):
            raise CoreError('QUALIFICATION_DISPATCH_DENIED')
        # The original CognitionSession ledger reserves each call first, including
        # failures/UNKNOWN, and enforces the unchanged nine-record/$0.40 ceilings.
        item = {'request_id': request.request_id, 'role': request.cognitive_role,
                'model_requested': port.model_id}
        calls.append(item)
        try:
            return original(port, request)
        finally:
            item.update(parser=port.last_parse_diagnostic.model_dump(mode='json') if port.last_parse_diagnostic else None,
                        http=port.last_http_observation.model_dump(mode='json') if port.last_http_observation else None,
                        provider_metadata=port.last_response_metadata)

    try:
        OpenAIJSONTransport.exchange = observed
        router = configured_router(home, cfg, resolver=resolver, authorized=True)
        from nana_core.life.__main__ import run
        run(home, seconds, headless=True, router=router, control_enabled=True)
        report['status'] = 'ORIGINAL_RUNTIME_STOPPED_NO_AUTOMATIC_REPLAY'
    finally:
        OpenAIJSONTransport.exchange = original
        scan_and_save(home, output, report, resolver)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, default=HOME)
    p.add_argument('--seconds', type=int, default=3600)
    p.add_argument('--output', type=Path, required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--private-terminal-binding', action='store_true')
    group.add_argument('--secret-fd', type=int)
    a = p.parse_args()
    resolver = secret_from_terminal() if a.private_terminal_binding else resolver_from_fd(a.secret_fd)
    try:
        report = start(a.home, a.seconds, a.output, resolver)
        print(json.dumps({'state': report['status'], 'calls': len(report['calls']), 'human_review': 'NOT_RUN'}))
    finally:
        resolver.clear()


if __name__ == '__main__':
    main()
