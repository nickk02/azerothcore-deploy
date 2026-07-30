# Finding: MMAP generator v20/v19 mismatch on Illidan (memory-safe, not the segfault cause)

file: `src/common/Collision/Management/MMapMgr.cpp:88-94` (mod-playerbots/azerothcore-wotlk)
scope: Illidan (Playerbots realm) only
severity: cosmetic/pathing-quality issue, not a crash risk
related: [findings/illidan-segfaults-playerbots-hypothesis.md](illidan-segfaults-playerbots-hypothesis.md)

Investigated whether the repeating `MMAP:loadMap: <tile>.mmtile was built with generator v20,
expected v19` warning in Illidan's `pb-worldserver` journal is connected to the two unexplained
segfaults. Short answer: the mismatch is real and pervasive, but the code path it triggers is
memory-safe by inspection, not a plausible direct cause of a segfault.

## Scope of the warning

Pulled the full warning history from `journalctl -u pb-worldserver` (retained journal covers
2026-07-25 through 2026-07-30, i.e. every boot since logging on this unit began):

- 29,476 total warning lines across the retained window.
- 1,684 distinct tile IDs affected, out of 3,780 total `.mmtile` files present in the server's
  `DataDir` -- **about 44.6% of all tiles on disk**.
- By map-ID prefix (first 3 digits of the tile filename):

  | map ID | warnings | map |
  |---|---|---|
  | 001 | 9,865 | Kalimdor |
  | 530 | 6,562 | Outland |
  | 000 | 6,503 | Eastern Kingdoms |
  | 571 | 6,322 | Northrend |
  | 369 | 218 | minor/instance map, not further identified |
  | 609 | 6 | minor/instance map, not further identified |

  All four main open-world continents are affected, not one isolated zone. This is pervasive,
  not a handful of stray tiles.
- Within a single boot, ~97% of that boot's warnings fire in the first minute (grid preload as
  the world loads and bots log in); the remaining ~3% trickle in over the following hour as
  bots/players move into grids not yet touched since startup. This matches on-demand,
  per-grid-activation tile loading, not a retry loop hammering the same tile.

## Provenance: extractor/binary version skew, not stale files

All 3,780 `.mmtile` files under the server's configured `DataDir` share a single, identical
mtime (2026-07-19), meaning they were deposited in one bulk copy/extraction pass, not
accumulated incrementally over time. That directory is
`/home/azerothcore/azeroth-server/data` (Sunstrider's data path, per
`playerbots-server/etc/worldserver.conf`'s `DataDir` setting) -- map/vmap/mmap client data is
shared between the two realms rather than duplicated per-realm, so it wasn't regenerated
specifically for the Playerbots fork.

The version numbers explain the rest:

- The exact commit running on Illidan is `ceeb3116e` (mod-playerbots/azerothcore-wotlk,
  Playerbot branch, dated 2026-07-24 -- confirmed against the `AzerothCore rev.` line in the
  journal). `MMAP_VERSION` at that exact commit is `19`
  (`src/common/Collision/Maps/MapDefines.h`).
- Upstream `azerothcore/azerothcore-wotlk` `master` currently defines `MMAP_VERSION` as `20`
  (confirmed against the live file on GitHub).

So the `.mmtile` files were extracted with a `mmaps_generator` build newer than (or divergent
from) what's compiled into Illidan's worldserver binary -- the Playerbots fork hasn't picked up
the upstream commit that bumped 19 to 20 yet. This is ordinary toolchain/binary version skew,
not file corruption or bit-rot.

## What the code actually does on a mismatch

`MMapMgr::LoadTile` (`src/common/Collision/Management/MMapMgr.cpp:68-122`) reads the fixed-size
tile header first, checks the magic number, then checks the version, all before ever touching
the tile's payload bytes:

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

On a version mismatch the function logs, closes the file, and returns `false` immediately. The
`dtAlloc`/`fread(data, fileHeader.size, ...)`/`navMesh->addTile(...)` block below it -- the part
that would actually parse the tile as Detour navmesh data -- is never reached. There is no
reinterpretation of a stale struct layout and no read of attacker-or-generator-controlled `size`
bytes when the version check fails. This rules out hypothesis (b) from the task: it's not
reading the mismatched tile with an incompatible layout.

The caller doesn't treat this as exceptional either.
`MapCollisionData::LoadMMapTile` -> `GridTerrainLoader::LoadMMap`
(`src/server/game/Grids/GridTerrainLoader.cpp:72-92`) maps the failure to
`MMAP_LOAD_RESULT_ERROR`, which just gets a `LOG_DEBUG` and nothing else -- no exception, no
retry storm (each tile is loaded once per grid activation, confirmed by the boot-time
distribution above).

The actual consumer, `PathGenerator::CalculatePath`
(`src/server/game/Movement/MovementGenerators/PathGenerator.cpp:57-87`), explicitly checks for
exactly this condition:

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

If either endpoint's tile isn't loaded, it builds a straight-line shortcut and returns
successfully. This is the same, pre-existing fallback AzerothCore uses for any map that has no
mmaps generated at all -- it is not a fragile or rarely-exercised branch.

## Plausibility assessment

**As a direct memory-safety cause of the segfaults: implausible.** The version check happens
before any read of the tile's payload, and the failure path back through `GridTerrainLoader` and
`PathGenerator` is exactly the same defensive fallback the engine already uses for maps with no
mmaps at all. Nothing in this path reads out of bounds or reinterprets incompatible data.

**As an indirect contributing factor: inconclusive, but not ruled out.** Roughly 45% of the
world's tiles -- across all four main continents -- are permanently forced onto the
straight-line shortcut path (`PATHFIND_NOT_USING_PATH`) instead of proper navmesh pathing, and
this has been true on every boot since journal retention begins. Illidan runs dozens of
Playerbots-controlled bots pathing continuously, so this fallback code executes far more often,
and across a far larger fraction of the map, than it would on a normal realm with a handful of
human players. Fallback branches that are rarely exercised on other realms get disproportionate
exercise here. That's a real structural difference worth keeping in mind, but this investigation
found no direct evidence -- no backtrace, no coredump, no log correlation -- tying an actual
crash to shortcut-path usage or to how Playerbots' own movement code consumes
`PATHFIND_NOT_USING_PATH` results (Playerbots' movement-generator code is not in this repo and
wasn't reviewed as part of this pass). Confirming or ruling this out needs either a backtrace
from the next crash (core dumps are now enabled per
[findings/illidan-segfaults-playerbots-hypothesis.md](illidan-segfaults-playerbots-hypothesis.md))
correlated against map/tile IDs, or a review of Playerbots' movement-generator handling of
shortcut paths at scale.

## Not done

Mmaps were not regenerated. Regeneration requires the original map/vmap client data extraction
and is a call for Nick to make, not something done as part of this investigation.

## Status

The generator-version mismatch is confirmed pervasive (44.6% of tiles, all four continents,
every boot) and confirmed memory-safe by direct code inspection. It's downgraded from "current
leading hypothesis" to "structural amplifier worth re-checking against the next backtrace, not a
standalone explanation" -- the Playerbots-hypothesis doc's core question (why does only the
bot-heavy realm crash) remains open.
