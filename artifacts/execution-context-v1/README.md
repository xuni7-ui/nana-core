# Execution Context V1 development delivery

This is the offline-qualified Core extension, not an updated deployed cloud image.

- Core exact source `9bc301c9fa3a06721cf9d143e0a19819ea6acfcd`.
- Operator tools exact source `7c842f4d089e1fcb93ff81b6eb4c8fd4af74a0f3`.
- Verify all files against `delivery.json` before unpacking with original `nana-unpack.py`.
- Use the matching installed Core release for diagnostic scripts; old images lack the new module.
- Read `docs/nana_execution_context_v1/INTEGRATION.md` for original Kernel/Grant integration.
- No automatic host SSH, credentials, Subject genesis, production installation or lifecycle operation.
