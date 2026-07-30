# Finding: InstanceSaveMgr.cpp day-alignment no-op bug

file: `src/server/game/Instances/InstanceSaveMgr.cpp:357`
scope: Sunstrider only (our fork's current state at that line; not confirmed on Illidan's older tree)
severity: minor, real bug, currently unfixed

Line 357 reads:

```cpp
t = (t * DAY) / DAY;
```

Multiplying by `DAY` and immediately dividing by `DAY` is a no-op -- `t` comes out unchanged.
The evident intent, matching the pattern used elsewhere in the same file (lines 302, 340, 582,
586), is day-truncation:

```cpp
t = (t / DAY) * DAY;
```

Integer division by `DAY` first (truncating to the start of the day), then multiplying back by
`DAY`, is the correct idiom. The current line just multiplies then divides back, restoring the
original value exactly (short of overflow), so whatever alignment this was meant to enforce
never happens.

This is why PR #26801 ("catch up missed global instance resets after downtime") doesn't apply
cleanly to our base: that PR's diff assumes the surrounding code already looks like upstream
master, which fixed this differently via #26711 (referenced in #26801's own PR body). Our fork's
divergent, still-buggy line 357 means the context lines don't match, so a straight cherry-pick
or patch of #26801 conflicts.

Not fixed as part of this backfill pass -- flagging for a follow-up single-line fix.
