# Finding: Illidan crash 4, double-delete of mod-assistant's `Assistant` script on shutdown

**Confidence: confirmed root cause.** Unlike
[illidan-crash-3-gameevent-visit-segfault.md](illidan-crash-3-gameevent-visit-segfault.md),
which is honest about being a plausible mechanism, this one is nailed down: there is a
backtrace naming the exact source line, the code at that line has an obvious and sufficient
defect, the deletion logic that trips over it is visible in core AzerothCore, and the
negative control (Sunstrider) differs in exactly the way the mechanism predicts.

**This finding corrects two earlier explanations that were both wrong.** See "What the
earlier theories got wrong" at the bottom before reusing anything from prior notes.

## Summary

`pb-worldserver` (Illidan) aborts with `double free or corruption (!prev)` on **every**
shutdown, without exception. The cause is in the third-party `mod-assistant` module:

```cpp
// modules/mod-assistant/src/mod_assistant.h:141
class Assistant : public CreatureScript, WorldScript
```

`Assistant` derives from two `ScriptObject` types. Its constructor therefore registers the
same `this` pointer into two different script registries. `ScriptMgr::Unload()` walks every
registry and `delete`s every pointer it holds, so the single `Assistant` instance is deleted
twice.

Nothing about OpenSSL, `needrestart`, or the database connection pools is involved.

**No data is at risk.** The crash happens strictly after every database pool has been
flushed and closed. Details under "Data safety" below.

## The evidence

### 1. It is not intermittent, and it is not shared with the other realm

Across the whole retained journal:

| service | clean stops (`Deactivated successfully`) | SIGSEGV |
|---|---|---|
| `pb-worldserver` (Illidan, Playerbots tree) | **0** | **21** |
| `ac-worldserver` (Sunstrider, upstream tree) | **18** | **0** |

Every single stop of `pb-worldserver` on record has ended in a signal. Every single stop of
`ac-worldserver` has been clean.

### 2. The backtrace

Coredump for PID 45436 (2026-07-31 06:07:54 UTC), thread 1, abridged to the frames that
matter:

```
#0  Acore::AbortHandler (...) at src/common/Debugging/Errors.cpp:154
#1  <signal handler called>
#2  pthread_kill ()
#3  raise ()
#4  abort ()
#5-#8  ?? () from libc.so.6                     <- glibc malloc consistency check
#9  non-virtual thunk to Assistant::~Assistant ()
      at modules/mod-assistant/src/mod_assistant.h:141
#10 operator()<ScriptTypeInfo<WorldScript, 13, false, true> > (...)
      at src/server/game/Scripting/ScriptMgr.cpp:161
#11 Acore::Impl::for_each<...ScriptMgr::Unload()::<lambda()> > (...)
#12 Acore::for_each<...> (...)
#13 ScriptMgr::Unload (this=...) at src/server/game/Scripting/ScriptMgr.cpp:157
#14 operator() (...) at src/server/apps/worldserver/Main.cpp:270
#15 std::_Sp_counted_deleter<...>::_M_dispose (...)
#16-#20 shared_ptr / __shared_count teardown
#21 main (...) at src/server/apps/worldserver/Main.cpp:420
```

Two details in frame #9 and #10 are the whole story:

- **`non-virtual thunk to Assistant::~Assistant()`.** A thunk in the destructor frame is the
  signature of destroying an object through a *secondary* base-class subobject pointer. That
  only exists under multiple inheritance. It tells you the delete came in via a base other
  than the primary one.
- **`ScriptTypeInfo<WorldScript, ...>`** in frame #10 names *which* registry was doing the
  deleting when it blew up: the `WorldScript` one. `CreatureScript` appears earlier in
  `ScriptRegistryTypes` than `WorldScript`, so the `CreatureScript` registry had already
  deleted the object on an earlier iteration; the `WorldScript` pass is the second delete.

### 3. The deletion logic, in core AzerothCore

`src/server/game/Scripting/ScriptMgr.cpp:155-168`:

```cpp
void ScriptMgr::Unload()
{
    Acore::for_each<ScriptRegistryTypes>([]<typename Info>()
    {
        for (auto const& [scriptID, script] : ScriptRegistry<typename Info::type>::ScriptPointerList)
        {
            delete script;
        }

        ScriptRegistry<typename Info::type>::ScriptPointerList.clear();
    });

    delete[] SpellSummary;
}
```

Each registry owns its pointers unconditionally and deletes all of them. There is no
shared-ownership tracking, no `seen` set, no guard against the same object appearing in two
registries. The design assumes one script object belongs to exactly one registry.

`Assistant` breaks that assumption. Its constructor runs both base constructors --
`CreatureScript` and `WorldScript` -- and each base constructor is what performs the
self-registration. Note that `WorldScript` is inherited *privately* here (there is no second
`public` keyword); that changes nothing, because private inheritance still runs the base
constructor and still registers.

### 4. The negative control

`ac-worldserver` is built from `azerothcore-wotlk`, whose `modules/` directory contains **no
modules at all** -- only the scaffolding (`CMakeLists.txt`, `ModulesLoader.cpp.in.cmake`,
`ModulesPCH.h`, `ModulesScriptLoader.h`, `create_module.sh`, `how_to_make_a_module.md`).

`pb-worldserver` is built from `playerbots-wotlk`, which carries 11 modules including
`mod-assistant`.

So the one process that loads `mod-assistant` is the one process that has never once shut
down cleanly, and the one that doesn't is the one that has never once failed to. That is
exactly what the mechanism predicts.

### 5. It is the only module with this defect

Scanned every module in the Playerbots tree for a class deriving from more than one
`*Script` base:

```
$ grep -rnE '^\s*class\s+\w+\s*:\s*public\s+\w*Script\w*\s*,' --include=*.h --include=*.cpp modules/
./mod-assistant/src/mod_assistant.h:141:class Assistant : public CreatureScript, WorldScript
```

One hit, across all 11 modules including `mod-playerbots` itself. This is an isolated bug in
one third-party module, not a pattern the tree is riddled with.

## Data safety

The crash cannot lose character data, and this is a structural guarantee rather than luck.

`src/server/apps/worldserver/Main.cpp` declares two scope guards in this order:

```cpp
std::shared_ptr<void> sScriptMgrHandle(nullptr, [](void*) { sScriptMgr->Unload(); });  // line 268
// ...
std::shared_ptr<void> dbHandle(nullptr, [](void*) { StopDB(); });                      // line 281
```

C++ destroys automatic objects in reverse order of declaration, so at shutdown `dbHandle`
runs **first** (`StopDB()`, closing every `DatabaseWorkerPool`) and `sScriptMgrHandle` runs
**second** (`ScriptMgr::Unload()`, where the double-delete happens).

The journal agrees. From the 2026-07-31 06:07 shutdown:

```
Halting process...
Logging out all bots...
Closing down DatabasePool 'acore_pb_characters'. Waiting for 0 queries to finish...
Asynchronous connections on DatabasePool 'acore_pb_characters' terminated. ...
All connections on DatabasePool 'acore_pb_characters' closed.
Closing down DatabasePool 'acore_pb_world'. Waiting for 0 queries to finish...
Asynchronous connections on DatabasePool 'acore_pb_world' terminatdouble free or corruption (!prev)
Caught signal 6
```

`acore_pb_characters` -- the database holding Fastopali and every bot -- reports `0 queries
to finish` and `All connections ... closed` before anything goes wrong. Bots are logged out
before that. The abort lands after the writes are already durable.

### The garbled log line is a red herring, and it matters

That `terminatdouble free or corruption` line is not a crash *inside* the world pool's
teardown. It is stdout (block-buffered under systemd, a trap already documented in
`deploy-state.md`) being cut into mid-flush by stderr, which is unbuffered. The abort message
jumps the queue.

This is why the apparent crash site *drifts between different pools* across occurrences:

- 2026-07-29 11:43 -- garbled at `acore_pb_auth`
- 2026-07-30 06:07 -- garbled at `Closing down Database...`
- 2026-07-31 06:07 -- garbled at `acore_pb_world`

The real crash site never moved. Only the position of the stdout buffer did. Anyone reading
these logs without the backtrace will conclude the DB pool teardown is at fault, and that
conclusion is wrong.

## The fix (not implemented, needs a rebuild)

Split `Assistant` into two classes, one per script type, which is what essentially every
other AzerothCore module does:

```cpp
class Assistant_CreatureScript : public CreatureScript { /* gossip hooks */ };
class Assistant_WorldScript    : public WorldScript    { /* OnAfterConfigLoad */ };
```

and register both in the module's `AddSC_*` loader. Shared configuration state moves to a
small struct or namespace-scope object both classes read, rather than being members of a
doubly-registered object.

This is a C++ change to a module in Illidan's tree, so it requires a full rebuild and
redeploy of `pb-worldserver`. **Per the standing rule, that is not something to run
unattended** -- it belongs with the already-staged Illidan module rebuild
(`~/ILLIDAN-REBUILD-STAGED.md`), with Nick present.

It is also worth reporting upstream to the `mod-assistant` maintainers; the defect is in
their module, not in anything local.

### Interim mitigation, already applied

`needrestart` was blacklisted for the AzerothCore services (see
[../ops/vm-storage-guards.md](../ops/vm-storage-guards.md) for the related infra work, and
`/etc/needrestart/conf.d/99-azerothcore.conf` on the VM). That does **not** fix this bug. It
removes one *trigger* -- the nightly `unattended-upgrades` run that was bouncing the live
realm around 06:07 UTC -- so Illidan stops taking two forced crash-restarts a week for no
reason. Every manual restart still crashes on the way down until the module is fixed.

## What the earlier theories got wrong

Both prior explanations should be discarded.

**"Heap corruption in `DatabaseWorkerPool` teardown."** No. The DB pools close cleanly and
log that they did. The association came entirely from the garbled log line described above.

**"Tearing down DB connections against a mid-replacement libssl/libcrypto."** No, and this
one is worth dwelling on because it looked genuinely convincing. The reasoning was that
`coredumpctl` showed `libssl.so.3 (deleted)` / `libcrypto.so.3 (deleted)` still mapped into
the crashed process, and that `unattended-upgrades` had upgraded `libssl3t64` seconds before
(dpkg log: `2026-07-31 06:07:35 upgrade libssl3t64:amd64 3.5.5-1ubuntu3.2 -> 3.5.5-1ubuntu3.3`,
crash at 06:07:39). Both facts are true. The inference from them is not, for two reasons:

1. **`ac-worldserver` was stopped in the same second, by the same `needrestart` pass, against
   the same half-replaced libssl -- and exited cleanly** (`06:07:37 ... Deactivated
   successfully`, with all three of its pools logging `All connections ... closed`). If a
   mid-replacement libssl were sufficient to corrupt the heap during teardown, it would have
   taken both processes down. It took neither; it was never the mechanism.
2. **Six of the eight recorded `Stopping pb-worldserver` events had no package activity at
   all** (2026-07-28 15:58, 2026-07-29 05:54 / 09:46 / 10:57 / 11:43 / 22:49). They crashed
   identically. Only two coincided with an OpenSSL upgrade.

The `(deleted)` mappings were a genuine observation that happened to be present in the two
dumps taken during a dpkg run, and they anchored the investigation onto a coincidence. The
correct read is the reverse of what was assumed: `needrestart` did not *cause* the crash, it
merely *caused a shutdown*, and every shutdown crashes.

## Relationship to crash 3 (the ~20:00 UTC one)

These remain two genuinely separate bugs, and the separation is now sharper than before.

Crash 4 (this one) only ever occurs when something asks the service to stop -- every instance
is immediately preceded by `Stopping pb-worldserver.service` in the journal.

Crash 3 has **no** `Stopping` line. From 2026-07-31 20:00, the entire journal record is:

```
20:00:20 systemd[1]: pb-worldserver.service: Main process exited, code=dumped, status=11/SEGV
```

Nothing requested a stop; the process died on its own mid-tick. That is a clean discriminator
between the two, usable on any future occurrence: **check whether a `Stopping` line precedes
the SIGSEGV.** If yes, it is this bug. If no, it is crash 3.

Both were previously conflated partly because `Acore::AbortHandler` (frame #0 above)
intercepts the `SIGABRT` from glibc and re-raises it as `SIGSEGV` to force a coredump, so
`coredumpctl list` renders them identically as `SIGSEGV`. That is a display artifact of the
abort handler, not a shared cause.

## Reproduction

Trivial and safe to confirm on the test realm, which is the recommended way to validate any
fix:

1. Add `mod-assistant` to a Sunstrider-style build (currently module-free).
2. `systemctl stop ac-worldserver` -> expect `double free or corruption`.
3. Apply the class split, rebuild, stop again -> expect `Deactivated successfully`.

Verifying on Illidan itself means restarting the live realm, which per standing rules happens
only during a confirmed 0-humans window.
