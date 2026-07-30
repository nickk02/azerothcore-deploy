# Incident: Sunstrider showing "(Down)" due to config-resolution trap

date: 2026-07-30
realm: Sunstrider (upstream realm, `ac-worldserver`)
status: resolved

## Symptom

Sunstrider showed as "(Down)" in the realm list even though the worldserver process was alive,
the port was listening, and the DB's `realmlist.flag` looked correct. All the usual liveness
checks passed while the realm was still effectively unreachable/misconfigured.

## Root cause

A worldserver binary was copied between two differently-prefixed CMake installs. AzerothCore's
default config-path resolution ties back to the `CMAKE_INSTALL_PREFIX` the binary was originally
built against, not the directory it's actually launched from. So the copied binary was silently
reading the WRONG install's `worldserver.conf` at runtime -- including its RealmID -- while the
config file sitting next to the binary on disk showed the correct value. See
docs/findings/cmake-install-prefix-config-trap.md for the general mechanism.

**Key lesson: a clean process-alive / port-listening / DB-flag check is not sufficient evidence
that a worldserver is actually serving the realm it's supposed to.** Only logging into the
realm from an actual game client and confirming the correct character list / world proved it.

## Fix

Both `ac-worldserver.service` and `pb-worldserver.service` now carry an explicit `-c <config
path>` argument in their systemd `ExecStart` line, removing any ambiguity about which config
each binary reads regardless of its original build prefix. Confirmed present on both units via
`systemctl cat` on the deploy VM as of 2026-07-29.

## Verification

This is the one row in the whole backlog that is `verified-in-game: yes` -- confirmed by Nick
actually logging into both realms and observing correct RealmID/character-list behavior after
the fix, not just a passive service/DB check.
