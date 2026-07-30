# Finding: Illidan pb-worldserver segfaults, Playerbots hypothesis (UNCONFIRMED)

Illidan's `pb-worldserver` has segfaulted twice: 2026-07-29 roughly 20:00 UTC, and again
~22:49 UTC during a restart. No backtrace was captured for either crash -- core-dump
infrastructure (systemd-coredump + `LimitCORE=infinity` on both worldserver units) was only
fixed AFTER both crashes, so the next crash will be debuggable, but these two weren't.

## Leading hypothesis (NOT confirmed)

Illidan is the only realm running Playerbots at all (40 bots running third-party AI
continuously). Sunstrider has zero players and no bots, so any Playerbots-specific bug
structurally cannot manifest there regardless of DB content. This is a simpler explanation than
any DB-content divergence between the two realms.

DB divergence was checked row-by-row for everything the 43-file SQL union touched (see
findings/43-file-union-and-filter.md) and found byte-identical between `acore_world` and
`acore_pb_world` on those tables -- ruling out DB content divergence as the direct cause.

## Status

Unconfirmed, not settled. Stated as a hypothesis, not a diagnosis. The next crash (now that
core dumps are enabled on both units) should produce an actual backtrace to test this against.
