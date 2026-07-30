# Finding: CMAKE_INSTALL_PREFIX config-resolution trap (Sunstrider "(Down)" bug)

Copying a worldserver binary between two differently-prefixed CMake installs makes it silently
fall back to reading the WRONG install's config file at runtime, because that binary's default
config-path resolution ties back to its original build prefix (baked in at compile time via
CMAKE_INSTALL_PREFIX), not the directory the binary is actually run from.

This is what caused the Sunstrider "(Down)" realm-list bug: the binary on disk looked fine
(process alive, port listening, correct RealmID visible in the adjacent config file), but the
actually-running process was still reading a stale config from its original build prefix,
serving the wrong RealmID. **A clean process-alive/port-listening/DB-flag check is NOT
sufficient evidence a worldserver is serving the realm it's supposed to.**

Fix: always pass an explicit `-c <config path>` in the systemd `ExecStart` line, or always
rebuild targeting the live prefix directly rather than copying just the binary.

This fix is already applied to both `ac-worldserver.service` and `pb-worldserver.service` on
the deploy VM (confirmed via `systemctl cat` on 2026-07-29 -- both units already carry an
explicit `-c` flag pointing at their respective `etc/worldserver.conf`). See
docs/incidents/2026-07-30-sunstrider-realmid-config-resolution.md for the incident writeup.
