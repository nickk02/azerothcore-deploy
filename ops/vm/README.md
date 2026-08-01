# VM system configuration

Copies of the system-level configuration installed on the azerothcore VM (10.0.0.85), kept
here so the VM's state is reviewable and reconstructible rather than living only on the box.

The directory layout mirrors the destination paths exactly: everything under `ops/vm/`
corresponds to the same path under `/` on the VM.

| file | purpose |
|---|---|
| `etc/needrestart/conf.d/99-azerothcore.conf` | Stops `needrestart` auto-restarting the AzerothCore services after library upgrades. See [findings/illidan-crash-4-mod-assistant-double-delete.md](../../docs/findings/illidan-crash-4-mod-assistant-double-delete.md). |
| `etc/systemd/coredump.conf.d/99-azerothcore.conf` | Caps the coredump store (`MaxUse`/`KeepFree`). |
| `etc/tmpfiles.d/99-ac-scratch.conf` | Creates `/var/tmp/ac-scratch`, the on-disk scratch dir for large files. |
| `etc/tmpfiles.d/tmp.conf` | Local override shortening the `/tmp` tmpfs age-out from 10d to 2d. |
| `etc/systemd/system/ac-diskguard.service` | Oneshot unit running the storage guard. |
| `etc/systemd/system/ac-diskguard.timer` | Fires the guard every 15 minutes. |
| `usr/local/sbin/ac-diskguard` | The guard script itself. |

Rationale and thresholds for the storage pieces are documented in
[docs/ops/vm-storage-guards.md](../../docs/ops/vm-storage-guards.md).

## Reinstalling

These are not auto-deployed. To apply after a change:

```bash
scp ops/vm/etc/needrestart/conf.d/99-azerothcore.conf        root@10.0.0.85:/etc/needrestart/conf.d/
scp ops/vm/etc/systemd/coredump.conf.d/99-azerothcore.conf   root@10.0.0.85:/etc/systemd/coredump.conf.d/
scp ops/vm/etc/tmpfiles.d/*.conf                             root@10.0.0.85:/etc/tmpfiles.d/
scp ops/vm/etc/systemd/system/ac-diskguard.*                 root@10.0.0.85:/etc/systemd/system/
scp ops/vm/usr/local/sbin/ac-diskguard                       root@10.0.0.85:/usr/local/sbin/
ssh root@10.0.0.85 'chmod 755 /usr/local/sbin/ac-diskguard && systemd-tmpfiles --create && systemctl daemon-reload && systemctl enable --now ac-diskguard.timer'
```

Verify afterwards:

```bash
ssh root@10.0.0.85 'systemd-analyze cat-config systemd/coredump.conf | grep -E "MaxUse|KeepFree"'
ssh root@10.0.0.85 'systemd-analyze cat-config tmpfiles.d/tmp.conf | grep "^q /tmp"'
ssh root@10.0.0.85 'systemctl start ac-diskguard.service && journalctl -t ac-diskguard -n 1'
```

`needrestart`'s effective decision for a given unit can be checked directly by loading its
config the same way `needrestart` does and running its own matching loop -- see the
verification section of [docs/ops/vm-storage-guards.md](../../docs/ops/vm-storage-guards.md).
