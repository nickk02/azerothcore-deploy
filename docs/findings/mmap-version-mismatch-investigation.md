# Finding: MMAP generator v20/v19 mismatch on Illidan. Memory-safe, not the segfault cause

file: `src/common/Collision/Management/MMapMgr.cpp:88-94` (mod-playerbots/azerothcore-wotlk)
scope: Illidan, the Playerbots realm, only
severity: pathing quality, not a crash risk
related: [findings/illidan-segfaults-playerbots-hypothesis.md](illidan-segfaults-playerbots-hypothesis.md)

Illidan's `pb-worldserver` journal repeats this warning: `MMAP:loadMap: <tile>.mmtile
was built with generator v20, expected v19`. I checked whether it connects to
the two unexplained segfaults.

It does not. The mismatch is real and it affects most of the world. The code
path it triggers is memory-safe by inspection.

## How widespread the warning is

I pulled the full warning history from `journalctl -u pb-worldserver`. The
retained journal covers 2026-07-25 to 2026-07-30, which is every boot since
logging began on this unit.

- 29,476 warning lines in the retained window.
- 1,684 distinct tile IDs, out of 3,780 `.mmtile` files in the server's
  `DataDir`. That is **44.6% of the tiles on disk**.

By map ID, taken from the first three digits of the tile filename:

| Map ID | Warnings | Map |
|---|---|---|
| 001 | 9,865 | Kalimdor |
| 530 | 6,562 | Outland |
| 000 | 6,503 | Eastern Kingdoms |
| 571 | 6,322 | Northrend |
| 369 | 218 | minor or instance map, not identified |
| 609 | 6 | minor or instance map, not identified |

All four open-world continents are affected. This is not a handful of stray
tiles.

Within one boot, about 97% of that boot's warnings fire in the first minute,
while the grids preload and the bots log in. The remaining 3% arrive over the
next hour as bots and players enter grids that startup did not touch. That
matches per-grid tile loading on demand. It is not a retry loop hitting one
tile.

## Cause: version skew between the extractor and the binary

All 3,780 `.mmtile` files under the configured `DataDir` share one identical
mtime, 2026-07-19. They arrived in a single bulk copy, not one at a time.

That directory is `/home/azerothcore/azeroth-server/data`, which is Sunstrider's
data path, set by `DataDir` in `playerbots-server/etc/worldserver.conf`. The two
realms share the map, vmap and mmap client data instead of holding a copy each,
so nobody regenerated it for the Playerbots fork.

The version numbers explain the rest.

- Illidan runs commit `ceeb3116e` of mod-playerbots/azerothcore-wotlk, Playerbot
  branch, dated 2026-07-24. I confirmed that against the `AzerothCore rev.` line
  in the journal. `MMAP_VERSION` at that commit is `19`, in
  `src/common/Collision/Maps/MapDefines.h`.
- Upstream `azerothcore/azerothcore-wotlk` `master` defines `MMAP_VERSION` as
  `20`. I confirmed that against the live file on GitHub.

So a `mmaps_generator` build newer than Illidan's worldserver extracted the
tiles. The Playerbots fork has not taken the upstream commit that moved 19 to
20. This is ordinary version skew between a tool and a binary. The files are not
corrupt.

## What the code does on a mismatch

`MMapMgr::LoadTile` (`src/common/Collision/Management/MMapMgr.cpp:68-122`) reads
the fixed-size tile header, checks the magic number, then checks the version. It
does all of that before it touches the payload:

```cpp
// read header
MmapTileHeader fileHeader;
if (fread(&fileHeader, sizeof(MmapTileHeader), 1, file) != 1 || fileHeader.mmapMagic != MMAP_MAGIC)
{
    LOG_ERROR("maps", "MMAP:loadMap: Bad header in mmap {:03}{:02}{:02}.mmtile", mapId, x, y);
    fclose(file);
    return false;
}

if (fileHeader.mmapVersion != MMAP_VERSION)
{
    LOG_ERROR("maps", "MMAP:loadMap: {:03}{:02}{:02}.mmtile was built with generator v{}, expected v{}",
                   mapId, x, y, fileHeader.mmapVersion, MMAP_VERSION);
    fclose(file);
    return false;
}

unsigned char* data = (unsigned char*)dtAlloc(fileHeader.size, DT_ALLOC_PERM);
```

On a version mismatch the function logs, closes the file and returns `false`. It
never reaches the `dtAlloc`, the `fread(data, fileHeader.size, ...)` or the
`navMesh->addTile(...)` below, which is the code that would parse the tile as
Detour navmesh data. Nothing reinterprets a stale struct layout, and nothing
reads `size` bytes chosen by the generator. This rules out hypothesis (b) from
the task: the server does not read the mismatched tile with an incompatible
layout.

The caller treats the failure as routine. `MapCollisionData::LoadMMapTile` calls
`GridTerrainLoader::LoadMMap` (`src/server/game/Grids/GridTerrainLoader.cpp:72-92`),
which maps the failure to `MMAP_LOAD_RESULT_ERROR`. That produces a `LOG_DEBUG`
and nothing else. There is no exception and no retry storm. Each tile loads once
per grid activation, which the boot-time distribution above confirms.

The consumer checks for this case directly.
`PathGenerator::CalculatePath`
(`src/server/game/Movement/MovementGenerators/PathGenerator.cpp:57-87`):

```cpp
// make sure navMesh works - we can run on map w/o mmap
// check if the start and end point have a .mmtile loaded (can we pass via not loaded tile on the way?)
Unit const* _sourceUnit = _source->ToUnit();
if (!_navMesh || !_navMeshQuery || (_sourceUnit && _sourceUnit->HasUnitState(UNIT_STATE_IGNORE_PATHFINDING)) ||
    !HaveTile(start) || !HaveTile(dest))
{
    BuildShortcut();
    _type = PathType(PATHFIND_NORMAL | PATHFIND_NOT_USING_PATH);
    return true;
}
```

If either endpoint's tile is absent, it builds a straight-line shortcut and
returns success. AzerothCore already uses this fallback for any map with no
mmaps at all, so it is well exercised.

## Assessment

**As a direct memory-safety cause of the segfaults: implausible.** The version
check runs before any read of the payload. The failure path through
`GridTerrainLoader` and `PathGenerator` is the same defensive fallback the engine
uses for maps with no mmaps. Nothing in that path reads out of bounds or
reinterprets incompatible data.

**As an indirect factor: inconclusive. Not ruled out.** About 45% of the world's
tiles, across all four continents, are permanently forced onto the straight-line
shortcut (`PATHFIND_NOT_USING_PATH`) instead of navmesh pathing. That has been
true on every boot in the retained journal.

Illidan runs dozens of Playerbots-controlled bots that path continuously, so
this fallback runs far more often, and over far more of the map, than on a realm
with a few human players. A branch that other realms rarely reach gets heavy use
here. That is a real structural difference and worth remembering.

This investigation found no direct evidence for it. There is no backtrace, no
coredump and no log correlation tying a crash to shortcut-path use, or to how
Playerbots' movement code consumes a `PATHFIND_NOT_USING_PATH` result. That
movement-generator code is not in this repository and I did not review it.

To settle it, either correlate the next crash's backtrace against map and tile
IDs, or review how Playerbots handles shortcut paths at scale. Core dumps are
now enabled. See
[findings/illidan-segfaults-playerbots-hypothesis.md](illidan-segfaults-playerbots-hypothesis.md).

## Not done

The mmaps were not regenerated. That needs the original map and vmap client data
extraction, and it is Nick's decision.

## Status

The version mismatch is confirmed widespread: 44.6% of tiles, all four
continents, every boot. It is confirmed memory-safe by direct code inspection.

It moves from "leading hypothesis" to "structural amplifier, re-check against
the next backtrace". It does not explain the crashes on its own. The core
question in the Playerbots-hypothesis document is still open: why does only the
bot-heavy realm crash?
