# Illidan module rebuild -- staged, NOT executed

Staged on 2026-07-29. Nothing here has been built. Run with Nick present.

## Module changes (done, filesystem only)

- Removed `~/playerbots-wotlk/modules/mod-junk-to-gold` (plain directory, not a
  git submodule -- confirmed no `.gitmodules` entry, safe `rm -rf`).
- Cloned `~/playerbots-wotlk/modules/mod-transmog` from
  `azerothcore/mod-transmog` (has its own `data/sql/db-world`,
  `data/sql/db-characters`, `data/sql/updates/world/` -- the updater will pick
  these up automatically per AzerothCore's module convention, no extra
  routing needed).
- Cloned `~/playerbots-wotlk/modules/mod-dungeon-clear` from
  **`jrad7/mod-dungeon-clear`, not the `azerothcore` org** (the org clone
  404'd -- this is a third-party module). Confirmed pure C++ (`src/`, `conf/`,
  no `sql/` anywhere) -- nothing to route through an updater for this one.

## ccache: installed but NOT verified working

`ccache -s` shows **0.0 / 5.0 GB, 0.00% used** -- the cache is empty. This
means either it has never been invoked by a prior build, or it isn't actually
wired into the compiler path. The brief asked for ccache "verified moving";
right now it is not verified, it's just present. Recommend passing it
explicitly rather than relying on a PATH shim:

```
-DCMAKE_CXX_COMPILER_LAUNCHER=ccache -DCMAKE_C_COMPILER_LAUNCHER=ccache
```

Check `ccache -s` again partway through the build to confirm hits are
accumulating before assuming -j3 will be fast.

## Ready-to-run build (do not run without Nick present)

```bash
cd ~/playerbots-wotlk
mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$HOME/playerbots-server \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DSCRIPTS=static -DMODULES=static
make -j3
make install
```

27G free on `/` -- plenty of headroom for the build.

## 43-file union reconciliation -- flagged for the same window, not resolved

The brief says to reconcile the union in this same maintenance window since a
fresh backup and rollback point exist anyway. Priority 1/2 already diagnosed
the divergence (the ScriptName-vs-binary mismatch, no DB-level corruption) but
didn't prescribe a fix -- that's still open. Whether "reconcile" means
recording the union in the `updates` table now, re-deriving a cleaner filter,
or something else needs Nick's call before the rebuild, not guessed at here.

## What actually needs Nick present

1. Confirm 0 humans on Illidan immediately before starting (standing rule).
2. Run the build above.
3. `make install` restarts nothing on its own -- the actual `systemctl restart
   pb-worldserver` to cut over is a separate, deliberate step after the build
   succeeds and the binary's rev banner is checked (per the round-2 lesson:
   verify the installed binary's own `AzerothCore rev.` string matches the
   branch tip you expect -- don't trust that a build finished "clean" without
   checking what actually got installed).
4. Decide the 43-file union question above before or during this window.
