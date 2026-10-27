# Unified release handoff

Core source9217e3f includes Real Living7a1bce9 and Execution Context9217e3f.
No credentials, Subject Store or private data included.

Verify image.json + all ordered image.tar.gz.partNNN with the supplied verify.py.
Concatenate in that order and docker load. Verify exact image ID before using it.
The image's default verify does not activate Core or create an identity.
Read docs/nana_first_life_unified_release/DEPLOY.md before any approved deployment.
Core.tar.gz is the exact source9217e3f portable package used inside this image.
No production cutover or authorization is conveyed by these files.
