"""Read-only namespace-qualified metadata. No SSH discovery or host mutation.

Use the installed qualified Python with an explicit release src on PYTHONPATH.
The process is labelled UNKNOWN, never automatically promoted to physical host.
A different requested target has no channel unless the application binds one.
"""

import argparse
import json

from nana_core.contracts import CoreError
from nana_core.execution_context.contracts import ContextBinding
from nana_core.execution_context.probe import LocalContextProbe
from nana_core.execution_context.routing import ExecutionChannel, ExecutionContextRouter, TargetBinding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-target", default="local-process")
    parser.add_argument("--target", default=None)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    try:
        probe = LocalContextProbe(ContextBinding(target_id=args.local_target, binding_id="operator.metadata"))
        context = probe.capture()
        router = ExecutionContextRouter(probe,
            targets=(TargetBinding(target_id=context.target_id, context_id=context.context_id,
                                   scope="UNKNOWN", channel_ids=("local.metadata",)),),
            channels=(ExecutionChannel("local.metadata", "LOCAL", probe),))
        result = router.diagnose(args.target or args.local_target, args.path)
    except (CoreError, ValueError) as exc:
        result = {"status": "BLOCKED", "code": exc.code if isinstance(exc, CoreError) else "EXECUTION_INPUT_INVALID",
                  "host_verified": False, "files_written": 0, "credentials_read": False}
        print(json.dumps(result, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
