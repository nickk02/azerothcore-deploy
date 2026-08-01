# Fix: snapshot the object store before game-event AI callbacks

Implements the fix recommended by
[illidan-crash-3-gameevent-visit-segfault.md](illidan-crash-3-gameevent-visit-segfault.md).
**Live on Sunstrider only. Not deployed to Illidan.**

Read the crash-3 doc's confidence framing first: the mechanism is a real, code-level hazard
sitting exactly on the crashing frame, but nobody has proven which creature's hook actually
triggers it. This change closes the hazard regardless of which hook does, since it makes the
whole class of trigger impossible.

## The change

`src/server/game/Events/GameEventMgr.cpp`, both overloads of
`GameEventAIHookWorker::Visit`. Before:

```cpp
for (auto const& p : creatureMap)
    if (p.second->IsInWorld() && ... && p.second->AI())
        p.second->AI()->sOnGameEvent(_activate, _eventId);
```

After: copy the pointers into a local `std::vector` first, then walk the copy. Same guards,
same order, same callbacks; the only difference is that the iteration is no longer over the
live container.

The hazard being closed: `sOnGameEvent()` runs arbitrary SmartAI actions, and an action such
as a same-map `SMART_ACTION_SUMMON_CREATURE` reaches `Creature::AddToWorld()`, which does
`GetMap()->GetObjectsStore().Insert<Creature>(...)` synchronously against the very container
being iterated. Inserting into an `std::unordered_map` can rehash it, and a rehash invalidates
every iterator into it, including the one the range-based `for` is still holding.

The gameobject overload has the identical shape and got the identical treatment.

## Why copying raw pointers is safe here

This was checked before writing the patch rather than assumed, because a careless "snapshot"
fix trades an iterator-invalidation bug for a use-after-free.

Object destruction in AzerothCore is deferred. `Map::AddObjectToRemoveList()`
(`Map.cpp:1792`) only inserts into `i_objectsToRemove`; the actual deletes happen in
`Map::RemoveAllObjectsInRemoveList()`, whose only caller is `Map::DelayedUpdate()`
(`Map.cpp:1776`, call at `Map.cpp:1789`).

`RunSmartAIScripts` runs on the `World::Update()` -> `GameEventMgr::Update()` path, which is a
different phase from `Map::DelayedUpdate()`. Nothing is freed part-way through a sweep, so the
copied pointers cannot dangle, and the existing per-element guards (`IsInWorld()`,
`IsDuringRemoveFromWorld()`, `FindMap()`) still correctly skip objects that were logically
removed during the sweep.

## Upstream

`GameEventAIHookWorker` is stock AzerothCore/TrinityCore engine code, not Playerbots-authored,
so this is worth upstreaming.

- **TrinityCore#26687, "Crash GameEventMgr::RunSmartAIScripts"** -- open since 2021-07-13, one
  comment. Directly on point.
- **TrinityCore#17587, "Crash i_AI"** -- **closed**, not open. Closed 2018-05-05 as
  `completed`, but the closing comment is "I presume this is no longer valid, more than a year
  with no crash", i.e. closed for staleness rather than because a fix landed. Earlier notes in
  this project listed both as "still-open upstream reports"; that was wrong about this one, and
  it is weak supporting evidence in any case. Cite #26687.

## Build and verification

Built on branch `fix/gameevent-visit-iterator-invalidation` (off `overnight-test-batch` at
`3b306d1ae`) in the isolated tree `~/azerothcore-wotlk/build-test`, whose
`CMAKE_INSTALL_PREFIX` is `~/azeroth-server-test`. Clean, 100%, exit 0.

**The revision banner still reads `3b306d1ae29f`, and that is expected, not a stale build.**
`revision_data.h` is generated at CMake *configure* time, not build time, so running `make`
without re-running `cmake` always leaves the banner behind. This exact trap already cost this
project a wrong conclusion once (see
[cmake-install-prefix-config-trap.md](cmake-install-prefix-config-trap.md) and the round-2
deploy notes). So the banner was deliberately *not* used as evidence.

Instead the binary was verified two independent ways:

1. **DWARF line table.** `objdump --dwarf=decodedline` on
   `GameEventMgr.cpp.o` lists lines 1901, 1902, 1916 and 1917 -- the
   `std::vector<Creature*> creatures;` / `creatures.reserve(...)` and their gameobject
   counterparts -- as having generated instructions. The new code is genuinely compiled in,
   not merely present in the source file.
2. **Chain of custody by timestamp.** source `00:31:45` -> object `00:37:47` -> linked binary
   `00:46:04`, all after the patch, with the live Illidan binary still dated `2026-07-25`.

## Deploy state

**Sunstrider (`ac-worldserver`, port 8085, `acore_world`): live.**

- Rollback binary saved first: `/home/azerothcore/backups/worldserver_rollback_pre-gameevent-fix.bin`.
- Swapped via copy-to-temp-then-rename (plain `cp` onto a running binary fails `ETXTBSY`).
- Player count re-checked at 0 immediately before the restart, not just earlier in the pass.
- Post-restart: `WORLD: World Initialized In 0 Minutes 8 Seconds`, `> RealmID: 2` read from its
  own boot log (the `-c <path>` fix holding), listening on 8085 confirmed via `ss -tln` rather
  than log silence, `ActiveState=active`, `NRestarts=0`, no new errors.
- The one message in the boot log that greps as an error, `Can't set process priority class,
  error: Permission denied`, is pre-existing and benign: 20 occurrences going back to
  2026-07-25, long predating this change.

**Illidan (`pb-worldserver`, port 8086, `acore_pb_world`): NOT deployed.** Binary untouched,
still dated 2026-07-25, 40 bots online, never restarted during this work. Deploying to the live
play realm is a judgment call left for Nick, and Illidan runs the Playerbots fork rather than
this tree, so it needs its own build.

## What this does and does not prove

It does not prove the crash is fixed. The crash fires at a daily 20:00 UTC event boundary on
**Illidan**, which does not have this build. Sunstrider has never exhibited crash 3 at all, so
there is nothing on Sunstrider to observe getting better.

What it proves: the change compiles, links, and boots a worldserver cleanly without regressing
startup. Confirmation would come from running it on Illidan across several 20:00 boundaries and
seeing the segfault stop, which is exactly the deploy decision being left for Nick.

`verified-in-game: no`, consistent with every other row in this repo.
