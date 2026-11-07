"""Installed DEV gateway then sourced note recall on the SAME stopped Subject.

Only a fresh owned scratch home is accepted by the original gateway probe.
Loopback language replies/hints are explicit fixtures, not real cognition or
human naturalness. No production/home/Vault, credential, device or social send.
Keep verify-dev.py beside this external qualification tool, outside Runtime.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def run(bundle, work, *, check_wire_reservations=False, check_retrieval_growth=False):
    if not __debug__:
        raise ValueError("QUALIFICATION_REQUIRES_ASSERTIONS")
    sys.dont_write_bytecode = True
    bundle = Path(bundle).resolve()
    work = Path(work).absolute()
    receipt = work.parent / (work.name + "-gateway-result.json")
    if receipt.exists():
        raise ValueError("FRESH_RECEIPT_REQUIRED")
    sibling = Path(__file__).with_name("verify-dev.py")
    if not sibling.is_file():
        sibling = Path(__file__).with_name("installed_gateway_probe.py")
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(sibling),
            "--bundle",
            str(bundle),
            "--work",
            str(work),
            "--output",
            str(receipt),
            "--check-memory-notes",
        ],
        check=True,
        timeout=90,
    )
    gateway = json.loads(receipt.read_text())
    if gateway["execution"] != "ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD":
        raise ValueError("EXPLICIT_DEVELOPMENT_ONLY")
    sys.path.insert(0, str(bundle / "src"))
    from nana_core.life.application import LifeApplication
    from nana_core.life.config import load_config, update_config
    from nana_core.life.memory_notes import save
    from nana_core.life.live_api.supervisor import existing_identity
    from nana_core.continuity.provider_config import (
        ProviderConfigurationAuthority,
        ProviderConfigService,
        ProviderCommand,
        ProviderProfile,
        ModelProfile,
        CapabilityRoute,
    )
    from nana_core.continuity.provider_routing import CapabilityRouter, RuntimeProviderFactory, RoutingPolicy
    from nana_core.continuity.providers import ProviderRegistry

    home = work / "life"
    marker = json.loads((home / "nana-space-development.json").read_text())
    identity, lineage, _ = existing_identity(home)
    if (
        marker != {"realm": "OWNED_DEVELOPMENT_ONLY", "identity_id": identity}
        or identity != gateway["subject_id"]
        or lineage != gateway["lineage_binding"]
    ):
        raise ValueError("DEV_IDENTITY_BINDING_MISMATCH")
    requests = []
    wire_lengths = []
    wire_reservations = []
    recall_terms = ["虹光约定"]
    growth_result = None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            wire_lengths.append(len(raw))
            body = json.loads(raw)
            request = json.loads(body["messages"][1]["content"])
            requests.append(request)
            proposal = {
                "interpretation": "SYNTHETIC installed fixture, not live semantic qualification",
                "source_refs": request["source_context_refs"],
                "uncertainty": "LOW",
                "confidence": 0.9,
            }
            if request["cognitive_role"] == "INTERPRET":
                proposal["dialogue"] = {"kind": "CHAT", "confidence": "HIGH", "recall_query_terms": list(recall_terms)}
            else:
                notes = [
                    json.loads(b["data_json"])
                    for b in json.loads(request["context_json"])["blocks"]
                    if b["kind"] == "MEMORY"
                    and json.loads(b["data_json"]).get("provenance") == "EXPLICIT_USER_NOTE_NOT_VERIFIED_WORLD_FACT"
                ]
                proposal["draft"] = {
                    "text": notes[0]["text"] if notes else "SYNTHETIC no supplied note",
                    "claim_memory_ids": [n["memory_id"] for n in notes],
                    "effect_status": request["role_input"]["dialogue"]["effect_status"],
                }
            raw = json.dumps(
                {
                    "model": body["model"],
                    "choices": [
                        {"finish_reason": "stop", "message": {"content": json.dumps(proposal, ensure_ascii=False)}}
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = load_config(home)
    fixture_call_limit = 6 if check_retrieval_growth else 4
    update_config(
        home,
        original.model_copy(
            update={
                "revision": original.revision + 1,
                "provider_calls_per_day": fixture_call_limit,
                "provider_calls_per_hour": fixture_call_limit,
                "per_provider_calls_per_day": fixture_call_limit,
                "provider_total_calls_limit": fixture_call_limit,
                "provider_context_tokens": 16384,
            }
        ),
        expected_revision=original.revision,
    )
    try:
        authority = ProviderConfigurationAuthority()
        service = ProviderConfigService(work / "synthetic-recall-providers.json", authority)
        service.initialize(authority)
        provider = ProviderProfile(
            provider_profile_id="installed.fixture",
            display_name="SYNTHETIC_LOOPBACK",
            protocol="SYNTHETIC_LOOPBACK",
            locality="LOCAL_FIXTURE",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            permitted_privacy=("PUBLIC", "PROJECT"),
        )
        model = ModelProfile(
            model_profile_id="installed.fixture.text",
            provider_profile_id=provider.provider_profile_id,
            remote_model_id="synthetic-installed-recall",
            model_version="1",
            operations=("COGNITION",),
            input_modalities=("TEXT",),
            output_modalities=("TEXT",),
            context_limit=16384,
            output_limit=2048,
        )
        for command in (
            ProviderCommand(operation="UPSERT_PROVIDER", expected_revision=0, provider=provider),
            ProviderCommand(operation="UPSERT_MODEL", expected_revision=1, model=model),
            ProviderCommand(
                operation="SET_CAPABILITY_ROUTE",
                expected_revision=2,
                route=CapabilityRoute(
                    operation="COGNITION",
                    primary_model_profile_id=model.model_profile_id,
                    permitted_privacy=("PUBLIC", "PROJECT"),
                ),
            ),
        ):
            service.update(command, authority)
        router = CapabilityRouter(
            service, RuntimeProviderFactory(ProviderRegistry(), None, RoutingPolicy(allow_synthetic_loopback=True))
        )
        with LifeApplication(home, router=router) as app:
            app.pause()
            text = "SYNTHETIC 合成资料：虹光约定安排在周五。"
            mid = save(app, text=text, privacy="PROJECT", request_id="installed.recall.note")["memory_id"]
            answer = app.chat("SYNTHETIC 请回忆这个项目约定", privacy="PROJECT", message_id="installed.recall.question")
            assert app.runtime.identity_id == identity
            assert len(requests) == 2 and mid in requests[-1]["source_context_refs"]
            assert answer["text"] == text and answer["render_state"] == "UNVERIFIED_MODEL_WORDING"
            assert not app.runtime.store.all("actions") and not app.runtime.store.all("lessons")
            if check_wire_reservations:
                for received, actual_bytes in zip(requests, wire_lengths, strict=True):
                    row = app.runtime.store.one("cognitive_requests", received["request_id"])
                    bound = min(131072, received["budget"]["output_tokens"] * 4 + 4096)
                    assert row["input_bytes"] == actual_bytes
                    assert row["reserved_bytes"] == actual_bytes + bound + 1
                    assert row["input_bytes"] + row["output_bytes"] <= row["reserved_bytes"]
                    wire_reservations.append(
                        {
                            "role": received["cognitive_role"],
                            "reserved_bytes": row["reserved_bytes"],
                            "actual_input_bytes": actual_bytes,
                            "response_hard_bound_bytes": bound,
                        }
                    )
        if check_retrieval_growth:
            from nana_core.clock import Clock
            from nana_core.presence.authority import VirtualClock
            from nana_core.presence.contracts import SECOND
            from nana_core.continuity.retrieval_growth import qualified_method
            from nana_core.continuity.records import RecordService

            clock = VirtualClock(Clock().utc_now_us())
            with LifeApplication(home, clock=clock) as app:
                app.pause(False)
                mids = [
                    save(
                        app,
                        text="SYNTHETIC " + word + " window Thursday.",
                        privacy="PROJECT",
                        request_id="installed.study." + str(i),
                    )["memory_id"]
                    for i, word in enumerate(("ＯＲＩＯＮ", "ＡＴＬＡＳ", "ＬＹＲＡ"))
                ]
                evaluator = app.runtime.work.note_retrieval_growth.evaluator
                before = evaluator.lookup("IDENTITY", ("ORION",), evaluator.snapshot("project-work"))
                assert before == []
                offered = app.runtime.work.note_retrieval_growth.slice("project-work")
                assert offered["note_retrieval"] == "OFFERED_TO_C" and not app.runtime.store.all("lessons")
            # Recover even the proposed spec before C's queued decision; same owner/Subject.
            with LifeApplication(home, clock=clock) as app:
                for _ in range(32):
                    clock.advance(SECOND)
                    app.runtime.step()
                selected = qualified_method(
                    app.runtime.store, app.runtime.authority, "project-user", "project-work", ("PROJECT",)
                )
                assert app.runtime.identity_id == identity and selected[1] == "UNICODE_WORDS"
                job = app.runtime.store.db.execute(
                    "SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                data = RecordService(app.runtime.store).read(job["record_id"])["payload"]
                assert job["state"] == "DONE" and data["results"]["BASELINE"]["passed"] == 0
                assert data["results"]["EVALUATE"]["all_passed"] and data["results"]["TRANSFER"]["all_passed"]
                later = save(
                    app,
                    text="SYNTHETIC ＡＬＴＡＩＲ later agreement Friday.",
                    privacy="PROJECT",
                    request_id="installed.study.later",
                )["memory_id"]
                app.pause()
            recall_terms[:] = ["ALTAIR"]
            before_calls = len(requests)
            with LifeApplication(home, clock=clock, router=router) as app:
                answer = app.chat(
                    "SYNTHETIC later independent note?", privacy="PROJECT", message_id="installed.learned.recall"
                )
                assert "ＡＬＴＡＩＲ" in answer["text"] and len(requests) == before_calls + 2
                assert later in requests[-1]["source_context_refs"] and app.runtime.identity_id == identity
                app.forget(mids[0])
                assert (
                    qualified_method(
                        app.runtime.store, app.runtime.authority, "project-user", "project-work", ("PROJECT",)
                    )
                    is None
                )
                answer = app.chat(
                    "SYNTHETIC after source withdrawal?", privacy="PROJECT", message_id="installed.learned.withdrawal"
                )
                assert answer["text"] == "SYNTHETIC no supplied note" and len(requests) == before_calls + 4
            growth_result = {
                "before_literal_found": False,
                "selected_method": selected[1],
                "independent_evaluation": True,
                "independent_transfer": True,
                "same_subject_restart": True,
                "later_new_note_in_actual_render_request": True,
                "source_withdrawal_fences_method": True,
                "scope": "INSTALLED_DEV_STORE_AND_LOOPBACK_FIXTURE_NOT_LIVE_MODEL_OR_HUMAN",
            }
        final_identity, final_lineage, _ = existing_identity(home)
        assert (final_identity, final_lineage) == (identity, lineage)
        return {
            **gateway,
            "installed_note_context_and_fixture_wording": "PASS_NOT_REAL_MODEL_RECALL",
            "same_subject_after_fixture_phase": True,
            "local_fixture_calls": len(requests),
            "real_provider_calls": 0,
            **({"retrieval_growth": growth_result} if growth_result else {}),
            **({"exact_wire_reservations": wire_reservations} if check_wire_reservations else {}),
        }
    finally:
        current = load_config(home)
        update_config(
            home, original.model_copy(update={"revision": current.revision + 1}), expected_revision=current.revision
        )
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-wire-reservations", action="store_true")
    parser.add_argument("--check-retrieval-growth", action="store_true")
    args = parser.parse_args()
    result = run(
        args.bundle,
        args.work,
        check_wire_reservations=args.check_wire_reservations,
        check_retrieval_growth=args.check_retrieval_growth,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
