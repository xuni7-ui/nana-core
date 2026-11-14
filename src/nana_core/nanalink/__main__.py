"""Run a separately configured, unprivileged NanaLink sidecar. No account login."""
import argparse
import asyncio
import signal
from pathlib import Path
from .sidecar import SidecarConfig, OneBotSidecar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--adapter-vault', required=True, help='isolated adapter-only host vault; never the full Core vault')
    parser.add_argument('--check', action='store_true', help='validate config without resolving secrets or opening connections')
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    if len(raw) > 65536:
        parser.error('configuration exceeds 64KiB')
    config = SidecarConfig.model_validate_json(raw)
    if args.check:
        print('NANALINK_CONFIG_VALID; no account or network accessed')
        return

    async def run():
        from ..life.provider_vault import DurableSecretResolver
        resolver = DurableSecretResolver(args.adapter_vault, initialize=False)
        sidecar = OneBotSidecar(config, resolver)
        done = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, done.set)
        try:
            await sidecar.start()
            await done.wait()
        finally:
            await sidecar.close()
            resolver.clear()
    asyncio.run(run())


if __name__ == '__main__':
    main()
