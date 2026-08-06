# VM storage guards

Controls that stop the azerothcore VM from running out of space again. Added on
2026-08-01, after `/tmp` reached 100%.

## What happened

`/tmp` on this VM is a **tmpfs**. It holds 7.6G and lives in RAM. It was found
completely full. It held three decompressed coredumps from earlier crash work:

```
3.5G  /tmp/core.latest
3.4G  /tmp/core.45436
710M  /tmp/core.0607     <- truncated; the filesystem ran out here
```

Two things made this worse than an ordinary full disk.

**It was RAM, not disk.** Those 7.6G competed with `pb-worldserver`, which holds
about 4G resident, and with MySQL. The VM has 16G in total.

**Nothing would have caught it.** The only control was the stock tmpfiles
age-out at 10 days. All three files were written on the same day. A 10-day timer
does not defend against 7.6G written in an afternoon.

The compressed originals stayed safe in `/var/lib/systemd/coredump`, so the
copies in `/tmp` were scratch and were deleted.

## The controls

Four layers, from passive to active. All are on the VM and tracked here.

### 1. Cap the coredump store

The file is `/etc/systemd/coredump.conf.d/99-azerothcore.conf`.

`pb-worldserver` dumps core on every stop, at about 620M compressed per dump.
See
[../findings/illidan-crash-4-mod-assistant-double-delete.md](../findings/illidan-crash-4-mod-assistant-double-delete.md).
At systemd's defaults that store grows to 10% of the root filesystem before
anything prunes it.

```ini
[Coredump]
Compress=yes
MaxUse=3G          # hard ceiling; oldest pruned first. 4 to 5 worldserver dumps.
KeepFree=10G       # never take the root fs below this, whatever MaxUse says
ProcessSizeMax=8G  # refuse rather than stall on a huge dump (worldserver is ~4G RSS)
ExternalSizeMax=8G
```

Check it with `systemd-analyze cat-config systemd/coredump.conf`.

### 2. A scratch directory on disk

The file is `/etc/tmpfiles.d/99-ac-scratch.conf`.

```
d /var/tmp/ac-scratch 1777 root root 3d
```

**Put large files in `/var/tmp/ac-scratch`. Never in `/tmp`.** That covers
extracted coredumps, decompressed database dumps and patch trees. This directory
is on the root filesystem, which has more than 23G free, and it ages out after
3 days through `systemd-tmpfiles-clean.timer`.

### 3. Shorten the tmpfs age-out

The file is `/etc/tmpfiles.d/tmp.conf`. It overrides
`/usr/lib/tmpfiles.d/tmp.conf` and takes `/tmp` from 10 days to 2.

```
q /tmp 1777 root root 2d
q /var/tmp 1777 root root 30d
```

This narrows the window. It is not the real protection. Layers 2 and 4 are.

### 4. Threshold guard

`ac-diskguard.timer` runs `/usr/local/sbin/ac-diskguard` every 15 minutes.
Layers 1 to 3 act only on their own schedule. This one reads the current numbers
and acts before anything reaches 100%.

Every run writes one INFO line, so you can grep the history:

```
$ journalctl -t ac-diskguard
root=70% used, 23G free | tmpfs /tmp=1% used | coredumps=2453M | scratch=1M
```

| Condition | Action |
|---|---|
| `/tmp` at 60% used or more | Warns and names the five largest entries. It reports only and never deletes, because tmpfs may hold somebody's work in progress. |
| Root free space below 15G | Warns only: "below warning threshold, not yet reclaiming". |
| Root free space below 10G | Reclaims. Deletes scratch entries older than 1 day, prunes coredumps beyond the newest 3, and runs `journalctl --vacuum-size=200M`. Logs every deletion by name. |

The script may delete from only three places: `/var/tmp/ac-scratch`, the
coredump store, and the journal. It never touches the contents of `/tmp`,
`/home`, the backups, or the databases.

## Verification

The branches that fire only under pressure were exercised against fake
directories. `COREDUMP_DIR` and `SCRATCH_DIR` were redirected and the thresholds
were forced, so the reclaim logic did not ship untested.

- The tmpfs warning fired and listed the offenders correctly.
- Scratch pruning removed the entry older than 1 day and kept the fresh one.
- Coredump pruning kept the newest 3 and removed the 2 oldest, by mtime.
- The journal vacuum ran.
- No unrelated service was affected.

The test directory was removed afterwards.

## Standing rule

**Large temporary files go in `/var/tmp/ac-scratch`, never in `/tmp`.**

`/tmp` on this VM is RAM. A 3.7G extracted core there is 3.7G the worldserver
does not get. Before you decompress a coredump, dump a large database, or unpack
a build tree, change to `/var/tmp/ac-scratch`. Delete the files when you finish
rather than waiting for the age-out.

## Baseline when this was written

```
/            76G total, 50G used, 23G free (70%)
/tmp         7.6G tmpfs, 76K used (1%)
coredumps    2.4G  (4 dumps)

/home/azerothcore        31G
  azerothcore-wotlk      18G   (Sunstrider build tree)
  azeroth-server         4.6G  (Sunstrider install)
  backups                2.9G
  playerbots-wotlk       2.3G  (Illidan build tree)
  playerbots-server      2.2G  (Illidan install)
  azeroth-server-test    1.4G
/var/lib/mysql           4.4G
```

`azerothcore-wotlk` at 18G is the largest single item, and most of it is build
output. It is not a problem with 23G free. It is the first place to look if the
root filesystem gets tight, because `make clean` on a stale build directory
reclaims most of it.
