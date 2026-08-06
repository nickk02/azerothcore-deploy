# Finding: Illidan crash 3, segfault in GameEventAIHookWorker::Visit

**Confidence: plausible mechanism, not a confirmed root cause.** I found a real
hazard in the code, and it sits on the crashing frame. I also found a data point,
event 89 and the creature Leprithus, that matches in time and in the call chain.

I could not show that the one game-event action tied to that creature performs
the container mutation the hazard needs. Read this as the mechanism plus the
strongest matching suspect. It is not the confirmed bug.

## The crash

PID 38378, SIGSEGV, 2026-07-30 20:00:01 UTC. Only the world update thread was
running. Every other thread sat in `epoll_wait`, `pthread_cond_wait`, `accept`
or `sleep`. This is a single-threaded crash inside `World::Update()`, not a race
between threads.

```
#0  GameEventAIHookWorker::Visit(std::unordered_map<ObjectGuid, Creature*>&)
#1  VisitorHelper<GameEventAIHookWorker, TypeList<Creature, GameObject, DynamicObject, Corpse, TypeNull>, ObjectGuid>(...)
#2  GameEventMgr::ApplyNewEvent(unsigned short)
#3  GameEventMgr::StartEvent(unsigned short, bool)
#4  GameEventMgr::Update()
#5  World::Update(unsigned int)
#6  WorldUpdateLoop()
#7  main
```

This is the first backtrace from any of the three Illidan crashes.
`findings/illidan-segfaults-playerbots-hypothesis.md` states that neither
earlier crash produced one, because the coredump setup was only fixed after
both. This is therefore the first hard evidence in the investigation, not extra
evidence on top of a tested hypothesis.

## The code iterates a live, mutable map

From `src/server/game/Events/GameEventMgr.cpp:1875-1900`:

```cpp
class GameEventAIHookWorker
{
public:
    GameEventAIHookWorker(uint16 eventId, bool activate) : _eventId(eventId), _activate(activate) { }

    void Visit(std::unordered_map<ObjectGuid, Creature*>& creatureMap)
    {
        for (auto const& p : creatureMap)
            if (p.second->IsInWorld() && !p.second->IsDuringRemoveFromWorld() && p.second->FindMap() && p.second->IsAIEnabled && p.second->AI())
                p.second->AI()->sOnGameEvent(_activate, _eventId);
    }
    ...
};

void GameEventMgr::RunSmartAIScripts(uint16 eventId, bool activate)
{
    sMapMgr->DoForAllMaps([eventId, activate](Map* map)
    {
        GameEventAIHookWorker worker(eventId, activate);
        TypeContainerVisitor<GameEventAIHookWorker, MapStoredObjectTypesContainer> visitor(worker);
        visitor.Visit(map->GetObjectsStore());
    });
}
```

`map->GetObjectsStore()` (`Map.h:352`) returns `MapStoredObjectTypesContainer&`,
which is
`TypeUnorderedMapContainer<TypeList<Creature, GameObject, DynamicObject, Corpse, TypeNull>, ObjectGuid>`
from `common/Dynamic/TypeContainer.h`. Remove the template machinery and the
`Visit` overload above iterates, by reference, the real
`std::unordered_map<ObjectGuid, Creature*>` that holds every creature on that
map. `ObjectAccessor` and every other subsystem use the same map to look
creatures up by GUID. It is not a snapshot and not a copy.

Other code mutates that same map synchronously:

- `Creature::AddToWorld()` (`Creature.cpp:310`):
  `GetMap()->GetObjectsStore().Insert<Creature>(GetGUID(), this);`
- `Creature::RemoveFromWorld()` (`Creature.cpp:357`):
  `GetMap()->GetObjectsStore().Remove<Creature>(GetGUID());`

Both run immediately rather than waiting for the next tick. `Map::AddToMap()`
(`Map.cpp:336`) calls the first, and `WorldObject::SummonCreature` and
`Map::SummonCreature` reach it for actions such as
`SMART_ACTION_SUMMON_CREATURE`. `Map::RemoveFromMap()` (`Map.cpp:739`) calls the
second, from the deferred remove-list processor at the start of the next
`Map::Update`. Ordinary despawns are therefore safe. See below.

The per-element guards in `Visit` are `IsInWorld()`, `!IsDuringRemoveFromWorld()`,
`FindMap()`, `IsAIEnabled` and `AI()`. They protect the current element from
being null or half destroyed. They do nothing for the container.

`sOnGameEvent()` calls `SmartAI::sOnGameEvent()` (`SmartAI.cpp:1284`), which
calls `ProcessEventsFor(SMART_EVENT_GAME_EVENT_START, ...)`. That runs arbitrary
SmartAI actions for whichever creature the callback reached. Suppose one of
those actions inserts into the creature map while the loop is running. A
same-map `SMART_ACTION_SUMMON_CREATURE` is the obvious candidate, and the
creature need not be the one whose event fired. An insert into a
`std::unordered_map` can force a rehash, and a rehash invalidates every iterator
into the map. The range-based `for` still holds one. That is undefined behaviour
and a textbook cause of a SIGSEGV, and it lands exactly on frame #0.

This is core AzerothCore code, not Playerbots code. `RunSmartAIScripts`,
`GameEventAIHookWorker`, `ApplyNewEvent` and `StartEvent` exist on any
AzerothCore fork that runs SmartAI game events.

## Event 89 is the event, and the only candidate with a matching action

Row 89 of `acore_pb_world.game_event` reads `start_time = 2016-10-28 20:00:00`,
`end_time = 2030-12-30 23:00:00`, `occurence = 1440` (daily) and `length = 600`
(10 hours). That start time puts the daily activation boundary at exactly
20:00:00, one second before the crash.

`GameEventMgr::Update()` schedules its own next call (`World.cpp:1292-1298`).
`_timers[WUPDATE_EVENTS]` takes the delay that `GameEventMgr::Update()` returns,
which is the minimum `NextCheck()` across every event. The scheduler is built to
fire on event boundaries, so hitting 20:00:00 or 20:00:01 when event 89
activates is expected. It is not a loose correlation.

`GameEventMgr::Update()` processes every due event in one pass, so I walked all
181 rows of `game_event` looking for another boundary at 2026-07-30 20:00:00. I
used the `world_event=0` rows, because holiday rows use a different state
machine. Two more matched:

- **Event 73, "Hourly Bells"**: `start_time` 01:00:00, `occurence=60`,
  `length=1`. It activates on every hour, so it also starts at 20:00:00.
- **Event 68, "AT Event Trigger (Horde Event)"**: `start_time` 06:55:00,
  `occurence=60`, `length=5`. Its window opened at 19:55:00 and ends at
  20:00:00.

Both queue in the same `activate` and `deactivate` sets inside this one
`GameEventMgr::Update()` call (`GameEventMgr.cpp:1247-1315`), and each triggers
its own full `RunSmartAIScripts` walk of every loaded map. Neither can be the
trigger:

- **Event 68 is a `StopEvent` and `UnApplyEvent` transition**, not `StartEvent`
  and `ApplyNewEvent`. Frame #3 of the backtrace is `GameEventMgr::StartEvent`,
  which event 68 never enters.
- **Event 73 has no matching `smart_scripts` rows.** `SELECT COUNT(*) FROM
  smart_scripts WHERE event_type=68 AND event_param1=73` returns 0. Every
  `AI()->sOnGameEvent(true, 73)` call is therefore a no-op, because
  `SmartScript.cpp:4674` reads `if (e.event.gameEvent.gameEventId != var0)
  return;`. Its `Visit()` pass touches every creature and does nothing.

Event 89 is the only one of the three that matches the `StartEvent` and
`ApplyNewEvent` frames and has a smart-script action that fires.

## What Leprithus's hook does

`game_event_creature` ties 6 GUIDs to event 89, all on map 0, Eastern Kingdoms.
Four are "Rotten Ghoul", entry 846, and two are "Leprithus", entry 572.
Leprithus is a nighttime rare spawn near Duskwood and Raven Hill.
`creature_template` shows both entries run pure SmartAI: `AIName = SmartAI` and
no C++ `ScriptName`.

Entry 572 has exactly one `smart_scripts` row hooked to a game event:

```
entryorguid=572  source_type=0(creature)  id=3  link=0
event_type=68 (SMART_EVENT_GAME_EVENT_START)  event_param1=89
action_type=70 (SMART_ACTION_RESPAWN_TARGET)  target_type=1 (SMART_TARGET_SELF)
```

Entry 846 has no game-event hook. So the entire scripted reaction to event 89
starting is Leprithus calling `Respawn()` on itself, from inside the
`AI()->sOnGameEvent()` call that `GameEventAIHookWorker::Visit` is making while
it iterates that map's creature store.

I read `Creature::Respawn()` (`Creature.cpp:2024-2157`) end to end to see
whether that call can touch `_objectsStore` and close the loop. In the case that
applies here, it cannot.

- `GameEventSpawn()` creates Leprithus for today's window through
  `new Creature; creature->LoadCreatureFromDB(...)`. `ApplyNewEvent` calls it
  before `RunSmartAIScripts`, so it does not run concurrently with this
  `Visit()`. Leprithus is therefore alive when its own
  `SMART_EVENT_GAME_EVENT_START` fires moments later.
- Illidan does not set `Respawn.DynamicMode` or
  `CONFIG_RESPAWN_FORCE_COMPATIBILITY_MODE` in
  `playerbots-server/etc/worldserver.conf`, so it uses the default:
  compatibility-mode respawn, with `_respawnCompatibilityMode = true`.
- In compatibility mode, the container-adjacent work in `Respawn()` is
  `UpdateEntry`, `SelectLevel`, `setDeathState(JustRespawned)`, `AI()->Reset()`
  and `UpdateObjectVisibility`. All of it is gated on `getDeathState() ==
  DeathState::Dead` (`Creature.cpp:2062`). A creature spawned this same tick is
  alive, so that block is skipped and the call falls through to a
  visibility-update no-op. Outside compatibility mode the same case is even more
  direct: `if (IsAlive()) return;` (`Creature.cpp:2131`).

So in the everyday firing of this action, which has presumably run daily since
the event's 2016 `start_time` with no recorded crash, I cannot find a path from
Leprithus's `SMART_ACTION_RESPAWN_TARGET` to a synchronous insert or erase on
`_objectsStore`.

Such a path would need Leprithus to be dead or decaying at the instant its own
respawn logic runs. I cannot check that state after the fact. The crash killed
the process before I could read live state, and I did not try to reconstruct it
from a script that is not running. This is the strongest matching suspect I
found. It is not confirmed.

I also checked `GameEventUnspawn()`, the half of `ApplyNewEvent` and
`UnApplyEvent` that removes creatures no longer needed by an active event. It
calls `creature->AddObjectToRemoveList()` (`GameEventMgr.cpp:1536`), which
defers to the remove list processed at the start of the next `Map::Update()`
tick. That is deliberately safe and does not explain a same-tick mutation.

## Does the bot population make this more likely?

Not the way the earlier hypothesis framed it.

`World::Update()` is single-threaded, and `GameEventMgr::Update()` runs to
completion before anything else takes a turn, bot AI ticks included. Bots are
not racing this container from a second thread, which is what the
"Playerbots-specific bug" language in findings 1 and 2 implied. The only way the
creature map changes during this `Visit()` call is as a synchronous, nested side
effect of the SmartAI callback the loop is making. That is driven by data: which
creatures carry `SMART_EVENT_GAME_EVENT_START` or `_END` hooks, and what those
hooks do.

Two things the bot population plausibly does change:

**Exposure.** Forty bots roam far more of the world than a mostly idle realm, so
far more grids stay loaded. `RunSmartAIScripts` walks every loaded map's entire
creature and gameobject store on every activation and deactivation. It calls
`AI()->sOnGameEvent()` on every `IsAIEnabled` creature it finds, whether or not
that creature's script cares about the event ID. More loaded grids means more
creatures visited per pass, and more chances that some creature's hook does
something container-mutating. A same-map summon is the concrete example. This is
general to every `RunSmartAIScripts` call the realm makes, and there are several
per day from the events above.

**Leprithus's state at spawn time.** Bots kill things more aggressively and more
persistently than human players idling in cities. If Leprithus were engaged,
near death, or dead and decaying at the moment its `GameEventSpawn()` and
`RunSmartAIScripts` cycle runs, `Respawn()` takes a different and much rarer
branch than the alive no-op path I traced. I did not trace every branch of the
`getDeathState() == Dead` respawn logic for `_objectsStore` side effects.

Both are code-grounded ways a bot-heavy realm raises exposure to a hazard that
already exists in the core engine. The hazard is
`GameEventAIHookWorker::Visit` iterating a live mutable per-map container from
inside reentrant AI callbacks with no mutation guard. It exists in stock
AzerothCore and could fire on any realm running SmartAI game events, given the
right creature data and timing. Playerbots does not need a bug for this to hit
Illidan harder than Sunstrider.

## Cross-reference with the first two crashes

`findings/illidan-segfaults-playerbots-hypothesis.md` covers two earlier
crashes, on 2026-07-29 at about 20:00 and about 22:49 UTC. Neither produced a
backtrace, because coredumps were wired up afterwards. That document's
"Playerbots-only, unconfirmed" hypothesis was never tested against a real crash
signature. It was inferred from "Illidan has bots, Sunstrider does not, and
Sunstrider has not crashed." This crash is the first chance to test it at all.

The first earlier crash was also at roughly 20:00 UTC, one day before this one,
in the same event-boundary window: event 89's daily 20:00:00 activation plus the
hourly boundaries of 73 and 68. That is a second same-time-of-day data point,
though without a backtrace it cannot confirm the same frame. The second earlier
crash, at about 22:49 UTC, matches no boundary I found in `game_event` and
happened during a restart, so it may be an unrelated startup problem.

I would restate the hypothesis as follows. **This is a same-tick,
single-threaded container-mutation hazard in core
`GameEventAIHookWorker::Visit`. Its odds of firing scale with how many creatures
each `RunSmartAIScripts` sweep visits and how much combat churn is happening on
those maps. Illidan's bot population raises both, and Playerbots itself does not
contain the bug.**

## What would make this confirmed

- A coredump from the next occurrence, now that coredumps work, showing the
  state of the creature map at the fault. Which GUID, which entry, inserted or
  erased, would settle it.
- Temporary instrumentation around a 20:00:00 boundary: a log line in
  `Creature::AddToWorld` and `RemoveFromWorld`, or a debug build under ASan, to
  catch a live insert or erase during a `Visit` pass.
- Reproducing Leprithus dying or despawning just before its 20:00:00 respawn
  window on a test realm, to see whether the `getDeathState() == Dead` branch of
  `Respawn()` mutates the container.

None of that was done here. This pass was read-only investigation against the
running production database and the matching source checkout. No game-event data
and no code was changed.
