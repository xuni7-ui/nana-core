# Independent installed qualification

This is an explicitly developer-operated OWNED_DEV local harness, not runtime
startup, identity, authority or a second Subject. It starts only its own local
services, checks actual files/IPC, original C/G/Kernel checkpoint repair and lawful
same-identity migration. No credential, provider, user desktop or social service.

Verify the separately published archive SHA256, extract to a fresh private
directory using Python tarfile data filter, then check SHA256SUMS. Use a short
fresh work path, e.g. /workspace/nana-staging/qv2-new-probe. Runtime excludes lab.py
and every demo/qualification entrypoint by an exact reviewed manifest.

```sh
<installed>/.venv/bin/python -I -c 'import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")' <installed>/src <qualification>/installed_probe.py --lab-source <qualification>/lab.py --bundle <installed> --root <fresh-short-path> --output <new-receipt.json>
```

Only the explicit addon lab is outside the installed runtime; its service child
also imports installed runtime. No repository PYTHONPATH or test-package import.
The default runtime never imports this addon and has no dependency on it.
