# VM storage guards

Durable controls so the azerothcore VM cannot run itself out of space again. Added
2026-08-01 after `/tmp` hit 100%.

## What happened

`/tmp` on the VM is a **tmpfs**, i.e. RAM-backed, 7.6G. It was found completely full. The
contents were three decompressed coredumps left behind by earlier crash investigations:

```
3.5G  /tmp/core.latest
3.4G  /tmp/core.45436
710M  /tmp/core.0607     <- truncated; this is where the filesystem ran out
```

Two things made this worse than an ordinary full-disk:

1. **It was RAM, not disk.** Those 7.6G were competing directly with the memory
   `pb-worldserver` (~4G RSS) and MySQL want. The VM has 16G total.
2. **Nothing would have caught it.** The only control in place was the stock tmpfiles
   age-out of 10 days. All three files were written the same day. A 10-day timer is no
   defence against 7.6G written in an afternoon.

The compressed originals were safe in `/var/lib/systemd/coredump` throughout, so the `/tmp`
copies were pure scratch and were deleted.

## The controls now in place

Four layers, from passive to active. All are on the VM and version-controlled here.

### 1. Cap the coredump store -- `/etc/systemd/coredump.conf.d/99-azerothcore.conf`

Until the shutdown double-free is fixed (see
[../findings/illidan-crash-4-mod-assistant-double-delete.md](../findings/illidan-crash-4-mod-assistant-double-delete.md)),
`pb-worldserver` dumps core on *every* stop, at ~620M compressed per dump. Left at systemd's
defaults that store may grow to 10% of the root filesystem before anything prunes it.

```ini
[Coredump]
Compress=yes
MaxUse=3G          # hard ceiling; oldest pruned first. ~4-5 worldserver dumps.
KeepFree=10G       # never take the root fs below this, whatever MaxUse says
ProcessSizeMax=8G  # refuse rather than stall writing a huge dump (worldserver is ~4G RSS)
ExternalSizeMax=8G
```

Verify with `systemd-analyze cat-config systemd/coredump.conf`.

### 2. A real on-disk scratch directory -- `/etc/tmpfiles.d/99-ac-scratch.conf`

```
d /var/tmp/ac-scratch 1777 root root 3d
```

**Use `/var/tmp/ac-scratch` for anything large. Never `/tmp`.** Extracted coredumps,
decompressed DB dumps, patch trees. It is on the root filesystem (23G+ free) rather than in
RAM, and it ages out at 3 days on its own via `systemd-tmpfiles-clean.timer`.

### 3. Shorten the tmpfs age-out -- `/etc/tmpfiles.d/tmp.conf`

Local override of `/usr/lib/tmpfiles.d/tmp.conf`, taking `/tmp` from 10 days to 2:

```
q /tmp 1777 root root 2d
q /var/tmp 1777 root root 30d
```

This narrows the window; it is not the real protection. Layers 2 and 4 are.

### 4. Threshold guard -- `ac-diskguard.timer` -> `/usr/local/sbin/ac-diskguard`

Runs every 15 minutes. Layers 1-3 are passive and only act on their own schedule; this one
looks at the actual numbers and acts before anything reaches 100%.

Every run emits one INFO line, so history is greppable:

```
$ journalctl -t ac-diskguard
root=70% used, 23G free | tmpfs /tmp=1% used | coredumps=2453M | scratch=1M
```

Thresholds and behaviour:

| condition | action |
|---|---|
| `/tmp` >= 60% used | WARNING + names the five largest entries. **Reports only, never deletes** -- tmpfs contents may be someone's in-flight work. |
| root free < 15G | WARNING only ("below warning threshold, not yet reclaiming") |
| root free < 10G | Reclaims: scratch entries older than 1 day, coredumps beyond the newest 3, `journalctl --vacuum-size=200M`. Logs every single deletion by name. |

It is deliberately narrow about what it may delete: only `/var/tmp/ac-scratch`, only the
coredump store, and the journal. It never touches `/tmp` contents, `/home`, backups, or the
databases.

## Verification performed

Not just installed -- the branches that only fire under pressure were exercised against fake
directories (redirected `COREDUMP_DIR`/`SCRATCH_DIR`, thresholds forced to trigger) so the
reclaim logic is not shipping untested:

- tmpfs warning fired and listed offenders correctly
- scratch pruning removed the >1-day entry and kept the fresh one
- coredump pruning kept the newest 3 and pruned the 2 oldest, by mtime
- journal vacuum ran
- unrelated services were unaffected

The test directory was removed afterwards.

## Standing rule

**Large temporary files go in `/var/tmp/ac-scratch`, never `/tmp`.**

On this VM `/tmp` is RAM. A 3.7G extracted core placed there is 3.7G the worldserver does not
get. If you are about to `zstd -d` a coredump, `mysqldump` something big, or unpack a build
tree, `cd /var/tmp/ac-scratch` first, and delete it when finished rather than relying on the
age-out.

## Baseline at time of writing

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

`azerothcore-wotlk` at 18G is the largest single item and is mostly build output. It is not
currently a problem with 23G free, but it is the first place to look if the root filesystem
ever gets tight -- a `make clean` on a stale build directory reclaims most of it.
