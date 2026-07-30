# Finding: merge-order lesson, #26822 vs #26854

#26822 sets creature 29355 (Embalming Slime (1)) immunity to -93. #26854, merged LATER
(2026-07-28 vs #26822's 2026-07-26), sets that same creature to -393. Blindly replaying a
backlog of merged PRs in file/discovery order rather than merge-date order can silently
regress a newer, correct fix with an older one touching the same row/column.

The actual fix applied to Sunstrider was #26822 minus the one conflicting line (creature
29355's immunity), preserving #26854's newer -393 value. Verified via SELECT: Sunstrider has
29355 at -393 while all of #26822's other targeted creatures (16017, 16018, 29347, 29353,
16029, 29356) carry #26822's values. See docs/prs/26822.md and docs/prs/26854.md.

**Lesson: when replaying a PR backlog, sort by merge date and treat a later merge's write to
the same column as authoritative.**

## Related discovery from this backfill pass

Illidan's copy of the same merge did NOT preserve this correctly across the board: entry 29356
ended up at -405 instead of #26822's intended -93 (see docs/prs/26822.md for the exact SELECT
evidence). This looks like a separate copy/paste slip during manual application to Illidan, not
a repeat of the 29355 merge-order issue -- flagging as a follow-up fix, not folding it into this
lesson.
