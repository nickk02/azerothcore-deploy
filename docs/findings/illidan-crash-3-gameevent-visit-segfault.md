# Finding: Illidan crash 3, segfault in GameEventAIHookWorker::Visit

**Confidence: plausible mechanism, not a confirmed root cause.** I found a real,
code-level hazard that sits exactly on the crashing frame, and a data point (event 89,
Leprithus) that lines up with it in time and in the call chain. I could not, however,
show that the one game-event action tied to that creature actually performs the container
mutation the hazard requires. Read this as "here is the mechanism and the strongest
matching suspect," not "here is the bug."

## The crash

PID 38378, SIGSEGV, 2026-07-30 20:00:01 UTC. Only the world update thread was active;
everything else was parked on epoll_wait/pthread_cond_wait/accept/sleep, so this is a
single-threaded crash inside `World::Update()`, not a race between threads:

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

This is the first backtrace either of the two prior Illidan crashes ever produced --
`findings/illidan-segfaults-playerbots-hypothesis.md` says plainly that no backtrace was
captured for either of them, because core-dump infrastructure was only fixed *after* both.
So this isn't new evidence layered on top of a tested hypothesis; it's the first hard
evidence in this whole investigation.

## The code: GameEventAIHookWorker::Visit iterates a live, mutable map

`src/server/game/Events/GameEventMgr.cpp:1875-1900`:

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

`map->GetObjectsStore()` (`Map.h:352`) returns `MapStoredObjectTypesContainer&` --
`TypeUnorderedMapContainer<TypeList<Creature, GameObject, DynamicObject, Corpse, TypeNull>, ObjectGuid>`
(`common/Dynamic/TypeContainer.h`). Strip the template machinery and the `Visit` overload
above is iterating, by reference, the *actual* `std::unordered_map<ObjectGuid, Creature*>`
that every creature on that map is registered in -- the same one `ObjectAccessor` and every
other subsystem uses to look creatures up by guid. It's not a snapshot or a copy.

That same map is mutated synchronously and unconditionally elsewhere:

- `Creature::AddToWorld()` (`Creature.cpp:310`): `GetMap()->GetObjectsStore().Insert<Creature>(GetGUID(), this);`
- `Creature::RemoveFromWorld()` (`Creature.cpp:357`): `GetMap()->GetObjectsStore().Remove<Creature>(GetGUID());`

Both are called synchronously (not deferred to next tick) from, among other places,
`Map::AddToMap()` (`Map.cpp:336`, used by `WorldObject::SummonCreature` /
`Map::SummonCreature` for e.g. `SMART_ACTION_SUMMON_CREATURE`) and from
`Map::RemoveFromMap()` (`Map.cpp:739`, used by the deferred remove-list processor at the
*start* of the next `Map::Update`, so ordinary despawns are actually safe against this --
see below).

The per-element guards in `Visit` (`IsInWorld()`, `!IsDuringRemoveFromWorld()`, `FindMap()`,
`IsAIEnabled`, `AI()`) only protect the *current* element `p.second` from being null or
half-torn-down. They do nothing for the container itself. `sOnGameEvent()` calls straight
into `SmartAI::sOnGameEvent()` (`SmartAI.cpp:1284`) → `ProcessEventsFor(SMART_EVENT_GAME_EVENT_START, ...)`,
which runs arbitrary SmartAI actions for whichever creature the callback landed on. If any
of those actions -- for *any* creature on that same map, not just the one whose event just
fired -- synchronously inserts into the creature map (a same-map `SMART_ACTION_SUMMON_CREATURE`
is the obvious one) while this range-based `for` is mid-flight, that's iterator invalidation
on `std::unordered_map` from inside its own iteration: an insert can force a rehash, which
invalidates every iterator into the map, and the loop is still holding one. That's a
textbook, engine-agnostic UB pattern for a SIGSEGV, and it maps exactly onto frame #0.

This is core AzerothCore game-event/SmartAI code, not anything Playerbots-authored --
`RunSmartAIScripts`, `GameEventAIHookWorker`, `ApplyNewEvent`, and `StartEvent` are all
upstream logic that exists on any AzerothCore fork running SmartAI game events.

## Event 89 (Leprithus) is the event, and it's the only one of three with a matching action

`acore_pb_world.game_event` row 89: `start_time = 2016-10-28 20:00:00`, `end_time =
2030-12-30 23:00:00`, `occurence = 1440` (daily), `length = 600` (10h). That start
time-of-day lands its daily activation boundary at exactly 20:00:00 -- one second before
the crash, and `GameEventMgr::Update()` self-schedules its own next call
(`World.cpp:1292-1298`, `_timers[WUPDATE_EVENTS]` set to the delay `GameEventMgr::Update()`
itself returns, computed as the minimum `NextCheck()` across every event) specifically to
land on event boundaries. This isn't a loose correlation -- the scheduler is built to fire
`Update()` right at 20:00:00/01, so hitting that exact second when event 89 activates is
expected, not coincidental.

But the task called out correctly that `GameEventMgr::Update()` processes every due event
in one pass, not just one, so I walked the full 181-row `game_event` table (`world_event=0`
rows, since world-event/holiday rows use a different state machine) looking for any other
row whose activation or deactivation boundary also lands on 2026-07-30 20:00:00. Two more
turned up:

- **Event 73, "Hourly Bells"** (`start_time` `01:00:00`, `occurence=60`, `length=1`) --
  activates on the hour, every hour, so it also starts at 20:00:00 today.
- **Event 68, "AT Event Trigger (Horde Event)"** (`start_time` `06:55:00`, `occurence=60`,
  `length=5`) -- its 5-minute window that opened at 19:55:00 *ends* at 20:00:00 today.

Both get queued in the same `activate`/`deactivate` sets inside this one `GameEventMgr::Update()`
call (`GameEventMgr.cpp:1247-1315`) and each triggers its own full `RunSmartAIScripts` walk
of every loaded map. I checked whether either could plausibly be the actual trigger instead
of event 89:

- **Event 68 is a `StopEvent`/`UnApplyEvent` transition**, not `StartEvent`/`ApplyNewEvent`.
  The backtrace's frame #3 is literally `GameEventMgr::StartEvent`, which rules event 68 out
  -- it never goes through that function.
- **Event 73 has zero matching `smart_scripts` rows** (`SELECT COUNT(*) FROM smart_scripts
  WHERE event_type=68 AND event_param1=73` → 0). Every creature's `AI()->sOnGameEvent(true, 73)`
  call is a guaranteed no-op (`SmartScript.cpp:4674`, `if (e.event.gameEvent.gameEventId !=
  var0) return;`), so its `Visit()` pass touches every creature but *does* nothing anywhere.

That leaves event 89 as the only one of the three that (a) matches the `StartEvent` →
`ApplyNewEvent` frames in the backtrace and (b) has any smart-script action that actually
fires.

## What Leprithus's game-event hook actually does

`game_event_creature` ties 6 guids to event 89, all on map 0 (Eastern Kingdoms): 4x "Rotten
Ghoul" (entry 846) and 2x "Leprithus" (entry 572). Leprithus is a nighttime rare spawn near
Duskwood/Raven Hill. `creature_template` confirms both entries run pure SmartAI (`AIName =
SmartAI`, no C++ `ScriptName`).

The full `smart_scripts` set for entry 572 has exactly one row hooked to game events:

```
entryorguid=572  source_type=0(creature)  id=3  link=0
event_type=68 (SMART_EVENT_GAME_EVENT_START)  event_param1=89
action_type=70 (SMART_ACTION_RESPAWN_TARGET)  target_type=1 (SMART_TARGET_SELF)
```

Rotten Ghoul (entry 846) has no game-event hook at all. So the entire scripted reaction to
event 89 starting is: Leprithus calls `Respawn()` on itself, from inside the very
`AI()->sOnGameEvent()` call that `GameEventAIHookWorker::Visit` is making mid-iteration over
that map's creature store.

I read `Creature::Respawn()` (`Creature.cpp:2024-2157`) end to end to see whether that call
can itself touch `_objectsStore` and close the loop. It can't, in the case that actually
applies here:

- `GameEventSpawn()` (called earlier in `ApplyNewEvent`, *before* `RunSmartAIScripts`, so not
  concurrent with this `Visit()`) is what creates Leprithus fresh for today's window via
  `new Creature; creature->LoadCreatureFromDB(...)`. It is therefore alive when its own
  `SMART_EVENT_GAME_EVENT_START` fires moments later.
- Illidan doesn't set `Respawn.DynamicMode`/`CONFIG_RESPAWN_FORCE_COMPATIBILITY_MODE` in
  `playerbots-server/etc/worldserver.conf`, so it runs the default (compatibility-mode
  respawn, `_respawnCompatibilityMode = true`).
- In compat mode, `Respawn()`'s only container-touching-adjacent work (`UpdateEntry`,
  `SelectLevel`, `setDeathState(JustRespawned)`, `AI()->Reset()`, `UpdateObjectVisibility`)
  is gated on `getDeathState() == DeathState::Dead` (`Creature.cpp:2062`). A creature that
  was just spawned this same tick is alive, not `Dead`, so that whole block is skipped; the
  call falls through to a visibility-update no-op. In non-compat mode the same "already
  alive" case is an even more direct no-op: `if (IsAlive()) return;` (`Creature.cpp:2131`).

So under the ordinary, everyday firing of this exact action -- which has presumably been
running daily since this event's `start_time` (2016) without a documented crash before now
-- I can't find a path from Leprithus's own `SMART_ACTION_RESPAWN_TARGET` to a synchronous
`_objectsStore` insert or erase. It would need Leprithus to already be dead/corpse-decaying
at the instant its own respawn logic runs (a state I have no way to check retroactively; the
crash killed the process before I could inspect live state, and I'm not attempting to
reconstruct it from a script that isn't running). I flag this as the strongest matching
suspect I found, not a confirmed one.

I also checked whether `GameEventUnspawn()` (the "remove creatures no longer needed by any
active event" half of `ApplyNewEvent`/`UnApplyEvent`) could be leaving a stale pointer in the
map: it calls `creature->AddObjectToRemoveList()` (`GameEventMgr.cpp:1536`), which defers to
the remove-list processed at the *start* of the next `Map::Update()` tick, not synchronously.
That's a deliberately safe pattern and doesn't explain a same-tick mutation.

## Does the Playerbots population actually make this more likely?

Not the way the earlier hypothesis framed it. `World::Update()` is single-threaded, and
`GameEventMgr::Update()` runs to completion before anything else (bot AI ticks included) gets
another turn -- so bots aren't concurrently racing this container from a second thread the
way findings #1/#2 implicitly assumed ("Playerbots-specific bug" language suggested a
concurrency angle). The only way the creature map gets mutated *during* this `Visit()` call
is as a synchronous, nested side effect of the very SmartAI callback the loop is making --
which is data-driven (which creatures have `SMART_EVENT_GAME_EVENT_START`/`_END` hooks and
what those hooks do), not bot-driven.

What Illidan's bot population plausibly *does* change:

- **Exposure.** Forty bots roam far more of the world at any given moment than a mostly-idle
  realm, which keeps far more grids loaded across far more maps. `RunSmartAIScripts` walks
  *every* loaded map's *entire* creature+gameobject store on every single event
  activation/deactivation, calling `AI()->sOnGameEvent()` on every `IsAIEnabled` creature it
  finds, regardless of whether that creature's script cares about this particular event ID.
  More loaded grids means more creatures visited per pass, which means more total chances
  that *some* creature's `SMART_EVENT_GAME_EVENT_START`/`_END` action anywhere in the world
  does something container-mutating (a same-map summon is the concrete example) during any
  given activation/deactivation sweep -- not specific to event 89, but general to every
  `RunSmartAIScripts` call this realm makes, of which there are several per day just from the
  events enumerated above (daily events, hourly events, etc).
- **Leprithus's own state at spawn time.** Bots kill things far more aggressively and
  persistently than human players idling in cities. If Leprithus (a rare, presumably
  aggressive nighttime mob) were engaged, near death, or already dead-and-decaying at the
  exact moment its own `GameEventSpawn()`/`RunSmartAIScripts` cycle runs, `Respawn()` takes a
  different, far-less-common branch than the "freshly spawned, alive, no-op" path I traced
  above -- and I did not fully trace every branch of `getDeathState() == Dead` respawn logic
  for `_objectsStore` side effects, given the scope of this pass.

Both of those are genuine, code-grounded ways a Playerbots-heavy realm increases *exposure*
to a pre-existing core-engine hazard, as opposed to the earlier framing that the bug is
somehow Playerbots-specific code. The hazard itself (`GameEventAIHookWorker::Visit` iterating
a live mutable per-map container from inside reentrant AI callbacks with zero mutation
guard) exists in stock AzerothCore and could in principle fire on any realm running SmartAI
game events, given the right creature data and the right timing. Playerbots doesn't need to
have a bug in it for this to bite Illidan harder than Sunstrider.

## Cross-reference with the first two crashes

`findings/illidan-segfaults-playerbots-hypothesis.md` covers two prior crashes (2026-07-29,
~20:00 and ~22:49 UTC) with **no captured backtrace for either** -- core dumps were only
wired up afterward. That doc's "Playerbots-only, unconfirmed" hypothesis was never actually
tested against a real crash signature; it was inferred purely from "Illidan has bots,
Sunstrider doesn't, Sunstrider hasn't crashed." This is the first crash in the whole series
with an actual backtrace, so it's not confirmation of that hypothesis so much as the first
opportunity to test it at all.

Notably: the *first* prior crash was also at roughly 20:00 UTC on 2026-07-29 -- one day
before this one, same time of day, same event-boundary window (event 89's daily 20:00:00
activation, plus 73 and 68's hourly boundaries). That's a second same-time-of-day data
point, for whatever it's worth without a backtrace to confirm it hit the same frame. The
second prior crash (~22:49 UTC) doesn't line up with any boundary I found in the `game_event`
table at that time and was during a restart, so it's plausibly an unrelated startup-path
issue rather than the same mechanism.

I'd revise the hypothesis from "Playerbots-specific bug" to: **a same-tick, single-threaded
container-mutation hazard in core `GameEventAIHookWorker::Visit`, whose odds of manifesting
scale with how many creatures get visited per `RunSmartAIScripts` sweep and how much combat
churn is happening on the maps involved -- both of which Illidan's bot population drives up
relative to a low-population realm, without Playerbots itself containing the bug.**

## What would move this from "plausible" to "confirmed"

- A core dump from the next occurrence (now that core-dumping is fixed) showing the actual
  dangling/corrupted state of the creature map at the point of the fault -- which guid, which
  entry, inserted or erased, would settle this definitively.
- Temporary instrumentation (a log line in `Creature::AddToWorld`/`RemoveFromWorld`, or a
  debug build under ASan) around a 20:00:00 boundary to catch a live insert/erase during a
  `GameEventAIHookWorker::Visit` pass in the act.
- Actually reproducing Leprithus dying/despawning right before its 20:00:00 respawn window on
  a test realm, to check whether the `getDeathState() == Dead` branch of `Respawn()` I didn't
  fully trace does something container-mutating.

None of that was done here -- this pass was read-only investigation against the running
production DB and the matching source checkout, per the task scope. No game-event data or
code was modified.
