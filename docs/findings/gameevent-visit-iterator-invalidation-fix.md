# Fix: snapshot the object store before game-event AI callbacks

Applies the fix recommended in
[illidan-crash-3-gameevent-visit-segfault.md](illidan-crash-3-gameevent-visit-segfault.md).
**Live on both realms. Sunstrider since 2026-08-01, Illidan since 2026-08-07.**

Read the confidence section of the crash-3 document first. The mechanism is a
real hazard in the code, and it sits on the crashing frame. Nobody has proved
which creature's hook triggers it. This change closes the whole class of
trigger, so the answer does not matter.

## The change

The file is `src/server/game/Events/GameEventMgr.cpp`. Both overloads of
`GameEventAIHookWorker::Visit` change. Before:

```cpp
for (auto const& p : creatureMap)
    if (p.second->IsInWorld() && ... && p.second->AI())
        p.second->AI()->sOnGameEvent(_activate, _eventId);
```

After, the code copies the pointers into a local `std::vector` and walks the
copy. The guards, the order and the callbacks are the same. The loop no longer
iterates the live container.

Here is the hazard it closes. `sOnGameEvent()` runs arbitrary SmartAI actions.
An action such as a same-map `SMART_ACTION_SUMMON_CREATURE` reaches
`Creature::AddToWorld()`, which calls
`GetMap()->GetObjectsStore().Insert<Creature>(...)`. That call is synchronous,
and it targets the container the loop is walking. An insert into a
`std::unordered_map` can rehash it. A rehash invalidates every iterator into
that map, including the one the range-based `for` still holds.

The gameobject overload has the same shape and gets the same change.

## Why the copied pointers are safe

I checked this before writing the patch. A careless snapshot trades an
iterator-invalidation bug for a use-after-free.

AzerothCore defers object destruction. `Map::AddObjectToRemoveList()`
(`Map.cpp:1792`) only inserts into `i_objectsToRemove`. The deletes happen in
`Map::RemoveAllObjectsInRemoveList()`. Its only caller is `Map::DelayedUpdate()`
(`Map.cpp:1776`, called at `Map.cpp:1789`).

`RunSmartAIScripts` runs on the `World::Update()` to `GameEventMgr::Update()`
path. That is a different phase from `Map::DelayedUpdate()`. Nothing is freed
during a sweep, so the copied pointers cannot dangle. The per-element guards
(`IsInWorld()`, `IsDuringRemoveFromWorld()`, `FindMap()`) still skip objects
that were removed during the sweep.

## Upstream

`GameEventAIHookWorker` is stock AzerothCore and TrinityCore engine code.
Playerbots did not write it, so the same defect exists upstream.

We do not report it. Fixes for this deployment are carried here and applied on
our own schedule. The reports below are recorded because they confirm the
defect is known and unfixed upstream, not as something to contribute to.

Practical consequence: this patch is local. Any future merge from either
upstream will drop it. Re-check both `Visit` overloads in
`src/server/game/Events/GameEventMgr.cpp` after a merge; if they iterate
`creatureMap` directly again instead of a snapshot, the hazard is back.

- **TrinityCore#26687, "Crash GameEventMgr::RunSmartAIScripts".** Open since
  2021-07-13, one comment. Directly on point. Cite this one.
- **TrinityCore#17587, "Crash i_AI".** Closed on 2018-05-05 as `completed`. The
  closing comment reads "I presume this is no longer valid, more than a year
  with no crash", so it closed for staleness and not because a fix landed.
  Earlier notes in this project called both reports open. That was wrong.

## Build and verification

Built on branch `fix/gameevent-visit-iterator-invalidation`, taken from
`overnight-test-batch` at `3b306d1ae`. The tree is `~/azerothcore-wotlk/build-test`
and its `CMAKE_INSTALL_PREFIX` is `~/azeroth-server-test`. The build finished
clean at 100% with exit 0.

**The revision banner still reads `3b306d1ae29f`. That is expected.**
`revision_data.h` is generated when CMake configures, not when the code builds,
so `make` without a fresh `cmake` always leaves the banner behind. This trap has
already produced one wrong conclusion in this project. See
[cmake-install-prefix-config-trap.md](cmake-install-prefix-config-trap.md). The
banner was therefore not used as evidence.

The binary was checked two other ways instead:

1. **DWARF line table.** `objdump --dwarf=decodedline` on `GameEventMgr.cpp.o`
   lists lines 1901, 1902, 1916 and 1917 as having generated instructions.
   Those lines hold `std::vector<Creature*> creatures;`, the matching
   `creatures.reserve(...)`, and the gameobject equivalents. The new code is
   compiled in, not merely present in the source.
2. **Timestamps.** Source at `00:31:45`, object at `00:37:47`, linked binary at
   `00:46:04`. All three follow the patch. The live Illidan binary is still
   dated 2026-07-25.

## Deploy state

**Sunstrider (`ac-worldserver`, port 8085, `acore_world`) is live.**

- A rollback binary was saved first, at
  `/home/azerothcore/backups/worldserver_rollback_pre-gameevent-fix.bin`.
- The swap copied to a temporary file and renamed it. A plain `cp` onto a
  running binary fails with `ETXTBSY`.
- The player count was re-checked at 0 immediately before the restart, not
  earlier in the pass.
- After the restart: `WORLD: World Initialized In 0 Minutes 8 Seconds`, and
  `> RealmID: 2` read from its own boot log, so the `-c <path>` fix holds. Port
  8085 was confirmed with `ss -tln` rather than by silence in the log.
  `ActiveState=active`, `NRestarts=0`, no new errors.
- One boot-log line matches a grep for errors: `Can't set process priority
  class, error: Permission denied`. It is benign and pre-existing, with 20
  occurrences going back to 2026-07-25.

**Illidan (`pb-worldserver`, port 8086, `acore_pb_world`): live since
2026-08-07.**

Illidan runs the Playerbots fork, so it needed its own build. That happened on
2026-08-06 alongside the mod-assistant class split and the module changes. The
same patch was applied to both `Visit` overloads in
`playerbots-wotlk/src/server/game/Events/GameEventMgr.cpp`.

Verified by DWARF on the built object, not by the revision banner:
`objdump --dwarf=decodedline` on `GameEventMgr.cpp.o` reports generated
instructions across lines 1893 to 1914, which is the new snapshot code in both
overloads.

The binary went live at Aug 07 20:00:42, when systemd auto-restarted the service
after that day's crash. That restart happened *after* the 20:00 boundary, so the
fix has not yet been tested against one.

## What this proves

It does not prove the crash is fixed. The crash fires at the daily 20:00 UTC
event boundary on Illidan. Illidan now has this build, but it only started
carrying it at Aug 07 20:00:42, after that day's boundary had already passed.
Sunstrider has never shown crash 3, so there is nothing there to observe.

The test is whether Illidan passes several 20:00 boundaries without a SIGSEGV.
Use the discriminator from the crash-4 document: a SIGSEGV with no preceding
`Stopping` line is crash 3.

It proves the change compiles, links and boots a worldserver without breaking
startup. Confirmation needs Illidan to run it across several 20:00 boundaries
with no segfault. That is the deploy decision left for Nick.

`verified-in-game: no`, like every other row in this repository.
