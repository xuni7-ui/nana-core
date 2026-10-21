# Portable Cloud Runtime — first run

Download archive, its published checksum and nana-unpack.py from the same release.
Use a Linux x86_64 host with Python3.12+venv; no root or production changes here.

```bash
python3 nana-unpack.py nana-first-life-portable-v1.tar.gz --sha256 228ef80e53ef961a409a651746a207a11a8bc72affe1940998e5c108fec9119a --destination ./nana-runtime
cd nana-runtime
./install.sh python3.12
./nana preflight
./nana init --fresh
./nana start
```

`init --fresh` creates a NEW Subject, not current Nana. Another authenticated SSH
terminal can run `./nana inspect`, `./nana health`, `./nana chat`, `./nana stop`.
All commands accept `--home /absolute/private/home`. By default they use var/subject
inside this new runtime, never guess or overwrite an existing Subject.

To move the current same Nana, **do not run init**. First install the code-only
bundle on the old trusted host; explicitly identify the existing original home:

```bash
./nana status --home /absolute/existing/subject-home
./nana stop --home /absolute/existing/subject-home
./nana export --home /absolute/existing/subject-home --retire-source --destination-id <fresh-UUID> --output /private/subject.zip
```

Only when you actually choose migration: export permanently retires the known
source before publishing. Save returned checksum/UUID. On a separately installed
new host, use an absent target home:

```bash
./nana restore --package /private/subject.zip --sha256 <returned-SHA256> --destination-id <same-UUID>
./nana inspect
./nana start
```

All old Grants are revoked. Bind new host settings and separately authorized
provider credentials through a memory FD or echo-disabled terminal; never argv,
env, .env, file, chat, logs or Store. This release neither uses nor resets the two
remaining development First-Life live slots. Offline chat is limited, not a human
naturalness qualification. No new real-server/social/device/production operations
have been performed. Read bundled MIGRATION/SECRETS/RECOVERY/LIMITATIONS before
actual migration; a quarantined review backup is not a runnable second writer.
