# Same Subject, lawful offline transfer

Do not migrate the actual development Nana merely to try this package. Use a
fresh test Subject first. This release includes no Subject package or database.

On trusted old host (stop first):

```
./nana stop
./nana export --retire-source --destination-id <fresh-UUID> --output /private/subject.zip
```

Save the returned SHA256, transfer ID, canonical identity, schema and destination
UUID. The official B8 export retires the old writer **before** publication. The
source cannot start again, even if a target import later fails. Never undo the
retirement, copy a DB, restore an older source snapshot or run both hosts. Retry a
failed export only to the identical destination and source commit, with a new
absent output path; preserve existing packages and failure evidence.

Transfer subject.zip privately and verify its SHA256 independently. It contains
sensitive Subject data even though it excludes credentials/host permissions. Do
not put it in the generic distribution archive, public Git, logs or a web folder.
Target install is separate; destination home must not exist:

```
./nana restore --package /private/subject.zip --sha256 <sha256> --destination-id <same-UUID>
./nana inspect
./nana preflight
./nana start
```

Identity/history/lineage transfer remain; all old Grants are revoked. Runtime
lease, host bindings/provider settings and credentials are not carried. Original
UNKNOWN requests/effects and reservations remain. Destination explicitly pauses
until review; no automatic action resumption or old message/provider replay.
Configure host resources/project material bindings separately, then reconsider
pending work. Old device/socket bindings are not portable permissions.

Do not delete/overwrite an occupied destination after a failed restore to hide
failure. Preserve quarantine for review and use another absent destination only
under the original bound transfer policy. B8 is offline single-operator transfer,
not cryptographic anti-copy or distributed multi-host consensus: keep exactly one
package/destination activation under the trusted operator. Do not duplicate it.

For upgrades: stop, produce a quarantined backup, separately install/check a new
runtime release, point it at the same stopped private home, preflight, start,
health. Host project paths may need an explicit CAS config rebind. Never git pull
over a live tree. No schema upgrade is performed by this schema13 bundle. Roll
back executable code only against a compatible current DB; do not reactivate a
stale DB or retired lineage. Moving backward between hosts requires another
lawful forward transfer, not an old database copy.
