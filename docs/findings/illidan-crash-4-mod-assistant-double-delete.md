# Finding: Illidan crash 4, double delete of mod-assistant's `Assistant` script on shutdown

**Confidence: confirmed root cause.** A backtrace names the exact source line.
The code at that line has a clear and sufficient defect. The deletion logic that
trips over it is visible in core AzerothCore. The negative control, Sunstrider,
differs in the way the mechanism predicts.

Compare
[illidan-crash-3-gameevent-visit-segfault.md](illidan-crash-3-gameevent-visit-segfault.md),
which states plainly that it describes only a plausible mechanism.

**This finding replaces two earlier explanations. Both were wrong.** Read "What
the earlier theories got wrong" before you reuse anything from older notes.

## Summary

`pb-worldserver` (Illidan) aborts with `double free or corruption (!prev)` on
every shutdown. There is no exception. The cause is in the third-party
`mod-assistant` module:

```cpp
// modules/mod-assistant/src/mod_assistant.h:141
class Assistant : public CreatureScript, WorldScript
```

`Assistant` derives from two `ScriptObject` types. Its constructor registers the
same `this` pointer in two different script registries. `ScriptMgr::Unload()`
walks every registry and deletes every pointer it holds, so it deletes the one
`Assistant` instance twice.

OpenSSL, `needrestart` and the database connection pools are not involved.

**No data is at risk.** The crash happens after every database pool has been
flushed and closed. See "Data safety" below.

## The evidence

### 1. It is consistent, and the other realm does not share it

Across the whole retained journal:

| Service | Clean stops | SIGSEGV |
|---|---|---|
| `pb-worldserver` (Illidan, Playerbots tree) | **0** | **21** |
| `ac-worldserver` (Sunstrider, upstream tree) | **18** | **0** |

Every recorded stop of `pb-worldserver` ended in a signal. Every recorded stop of
`ac-worldserver` was clean.

### 2. The backtrace

From the coredump for PID 45436, taken 2026-07-31 06:07:54 UTC, thread 1. Only
the frames that matter:

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

Two details carry the whole finding.

**Frame #9 reads `non-virtual thunk to Assistant::~Assistant()`.** A thunk in a
destructor frame means the object was destroyed through a secondary base-class
subobject pointer. That case exists only under multiple inheritance. The delete
therefore arrived through a base other than the primary one.

**Frame #10 names `ScriptTypeInfo<WorldScript, ...>`.** That is the registry that
was deleting when the process aborted. `CreatureScript` comes before
`WorldScript` in `ScriptRegistryTypes`, so the `CreatureScript` registry had
already deleted the object on an earlier pass. The `WorldScript` pass is the
second delete.

### 3. The deletion logic in core AzerothCore

From `src/server/game/Scripting/ScriptMgr.cpp:155-168`:

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

Each registry owns its pointers and deletes all of them. There is no shared
ownership, no `seen` set, and no guard against one object appearing in two
registries. The design assumes each script object belongs to one registry.

`Assistant` breaks that assumption. Its constructor runs both base constructors,
`CreatureScript` and `WorldScript`, and each base constructor registers the
object. Note that `WorldScript` is inherited privately, because there is no
second `public` keyword. That changes nothing. Private inheritance still runs
the base constructor and still registers.

### 4. The negative control

`ac-worldserver` is built from `azerothcore-wotlk`. Its `modules/` directory
holds no modules, only the scaffolding: `CMakeLists.txt`,
`ModulesLoader.cpp.in.cmake`, `ModulesPCH.h`, `ModulesScriptLoader.h`,
`create_module.sh` and `how_to_make_a_module.md`.

`pb-worldserver` is built from `playerbots-wotlk`, which carries 11 modules,
including `mod-assistant`.

The one process that loads `mod-assistant` has never shut down cleanly. The one
that does not load it has never failed to. That is what the mechanism predicts.

### 5. No other module has this defect

I scanned every module in the Playerbots tree for a class that derives from more
than one `*Script` base:

```
$ grep -rnE '^\s*class\s+\w+\s*:\s*public\s+\w*Script\w*\s*,' --include=*.h --include=*.cpp modules/
./mod-assistant/src/mod_assistant.h:141:class Assistant : public CreatureScript, WorldScript
```

One hit across all 11 modules, including `mod-playerbots`. This is an isolated
bug in one third-party module.

## Data safety

The crash cannot lose character data. That is a structural guarantee, not luck.

`src/server/apps/worldserver/Main.cpp` declares two scope guards in this order:

```cpp
std::shared_ptr<void> sScriptMgrHandle(nullptr, [](void*) { sScriptMgr->Unload(); });  // line 268
// ...
std::shared_ptr<void> dbHandle(nullptr, [](void*) { StopDB(); });                      // line 281
```

C++ destroys automatic objects in reverse order of declaration. At shutdown
`dbHandle` runs first and calls `StopDB()`, which closes every
`DatabaseWorkerPool`. `sScriptMgrHandle` runs second and calls
`ScriptMgr::Unload()`, where the double delete happens.

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

`acore_pb_characters` holds Fastopali and every bot. It reports `0 queries to
finish` and `All connections ... closed` before anything goes wrong, and the
bots log out before that. The abort lands after the writes are durable.

### The garbled log line is a red herring

The line `terminatdouble free or corruption` is not a crash inside the world
pool's teardown. Stdout is block-buffered under systemd, a trap already recorded
in `deploy-state.md`. Stderr is unbuffered, so the abort message cuts into the
middle of a stdout flush.

This is why the apparent crash site moves between pools:

- 2026-07-29 11:43, garbled at `acore_pb_auth`
- 2026-07-30 06:07, garbled at `Closing down Database...`
- 2026-07-31 06:07, garbled at `acore_pb_world`

The real crash site never moved. Only the stdout buffer position moved. Anyone
who reads these logs without the backtrace will blame the database pool
teardown, and that is wrong.

## The fix

Not implemented. It needs a rebuild.

Split `Assistant` into one class per script type, which is what nearly every
other AzerothCore module does:

```cpp
class Assistant_CreatureScript : public CreatureScript { /* gossip hooks */ };
class Assistant_WorldScript    : public WorldScript    { /* OnAfterConfigLoad */ };
```

Register both in the module's `AddSC_*` loader. Move the shared configuration
state into a small struct or a namespace-scope object that both classes read.
Do not keep it in members of a doubly-registered object.

This is a C++ change to a module in Illidan's tree, so it needs a full rebuild
and redeploy of `pb-worldserver`. **The standing rule says do not run that
unattended.** It belongs with the staged Illidan module rebuild
(`~/ILLIDAN-REBUILD-STAGED.md`), with Nick present.

Report it to the `mod-assistant` maintainers as well. The defect is in their
module.

### Interim mitigation, already applied

`needrestart` is blacklisted for the AzerothCore services. See
[../ops/vm-storage-guards.md](../ops/vm-storage-guards.md) and
`/etc/needrestart/conf.d/99-azerothcore.conf` on the VM.

This does not fix the bug. It removes one trigger: the nightly
`unattended-upgrades` run that bounced the live realm at about 06:07 UTC. Illidan
therefore stops taking two forced crash-restarts a week. Every manual restart
still crashes until the module is fixed.

## What the earlier theories got wrong

Discard both.

**"Heap corruption in `DatabaseWorkerPool` teardown."** No. The pools close
cleanly and log that they did. The idea came entirely from the garbled log line
above.

**"Tearing down DB connections against a half-replaced libssl or libcrypto."**
No. This one is worth explaining, because it looked convincing.

The reasoning ran like this. `coredumpctl` showed `libssl.so.3 (deleted)` and
`libcrypto.so.3 (deleted)` still mapped into the crashed process.
`unattended-upgrades` had upgraded `libssl3t64` seconds earlier: the dpkg log
reads `2026-07-31 06:07:35 upgrade libssl3t64:amd64 3.5.5-1ubuntu3.2 ->
3.5.5-1ubuntu3.3`, and the crash follows at 06:07:39. Both facts are true. The
conclusion drawn from them is not, for two reasons.

1. **`ac-worldserver` stopped in the same second, from the same `needrestart`
   pass, against the same half-replaced libssl, and exited cleanly.** The
   journal reads `06:07:37 ... Deactivated successfully`, and all three of its
   pools logged `All connections ... closed`. A half-replaced libssl that
   corrupts the heap during teardown would have taken both processes down. It
   took neither.
2. **Six of the eight recorded `Stopping pb-worldserver` events had no package
   activity at all.** Those are 2026-07-28 15:58 and 2026-07-29 at 05:54, 09:46,
   10:57, 11:43 and 22:49. They crashed the same way. Only two coincided with an
   OpenSSL upgrade.

The `(deleted)` mappings were a real observation. They appeared in the two dumps
that were taken during a dpkg run, and they anchored the investigation to a
coincidence. Read it the other way round: `needrestart` did not cause the crash.
It caused a shutdown, and every shutdown crashes.

## Relationship to crash 3

These are two separate bugs. The line between them is now sharp.

Crash 4, this one, occurs only when something asks the service to stop. Every
instance follows a `Stopping pb-worldserver.service` line in the journal.

Crash 3 has no `Stopping` line. The entire journal record from 2026-07-31 20:00
is:

```
20:00:20 systemd[1]: pb-worldserver.service: Main process exited, code=dumped, status=11/SEGV
```

Nothing asked it to stop. The process died mid-tick.

**Use that as the discriminator on any future occurrence: check whether a
`Stopping` line precedes the SIGSEGV.** If it does, this is crash 4. If it does
not, it is crash 3.

The two were conflated partly because `Acore::AbortHandler`, frame #0 above,
catches the `SIGABRT` from glibc and re-raises it as `SIGSEGV` to force a
coredump. `coredumpctl list` therefore shows both as `SIGSEGV`. That is a
display artifact of the abort handler, not a shared cause.

## Reproduction

This is safe to confirm on the test realm, and that is the way to validate a fix.

1. Add `mod-assistant` to a Sunstrider-style build, which currently has no
   modules.
2. Run `systemctl stop ac-worldserver`. Expect `double free or corruption`.
3. Apply the class split, rebuild, and stop it again. Expect `Deactivated
   successfully`.

Verifying on Illidan means restarting the live realm. Under the standing rules
that happens only in a confirmed zero-player window.
