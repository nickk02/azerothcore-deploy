# C++ deploys currently live

## Sunstrider (upstream realm)

Runs branch `overnight-test-batch` at rev `3b306d1ae29f`. This branch has ELEVEN cherry-picked
PRs compiled directly into the running worldserver binary:

Round 1: #26834, #26809, #26818, #26833, #26845, #26565
Round 2: #26828, #26816, #26466, #26838, #26830

**Plus one local (non-PR) engine fix, deployed 2026-08-01:** the
`GameEventAIHookWorker::Visit` iterator-invalidation fix, on branch
`fix/gameevent-visit-iterator-invalidation` off `overnight-test-batch`. See
[gameevent-visit-iterator-invalidation-fix.md](gameevent-visit-iterator-invalidation-fix.md).
Rollback binary at `/home/azerothcore/backups/worldserver_rollback_pre-gameevent-fix.bin`.

**The revision banner still reads `3b306d1ae29f` and will keep doing so** until someone
re-runs `cmake`, because `revision_data.h` is generated at configure time. Do not use the
banner to decide what a binary contains -- grep the binary, or check the DWARF line table.

**None of these eleven has been exercised or tested in an actual game client yet.** They are
compiled into the live binary and nothing more -- every one of them should be treated as
`applied` (in the sense that the code is running) but `verified-in-game: no` if it were tracked
in docs/prs/ (it isn't, since these came in as a C++ batch rather than individual DB-tracked
PRs in this backfill).

## Illidan (Playerbots realm)

Runs its own stock Playerbots-fork build, untouched by any of the eleven PRs above. Any C++-only
or paired PR in docs/prs/ marked "not in the eleven-PR cherry-pick list" is therefore also NOT
compiled into Illidan's binary -- its build predates all of them.

## Cross-reference

When a doc in docs/prs/ has `type: cpp-only` or `type: paired` and says "not in the eleven-PR
cherry-pick list", that means: the C++ half of that PR is running on NEITHER realm's binary
right now, regardless of what SQL half might be sitting in either database.
