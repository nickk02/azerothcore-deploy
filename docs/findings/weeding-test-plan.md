# Weeding test plan: shortest path to the most `verified` rows

Scope: only the 16 rows currently `status: applied` can move to `verified`. Skipped/unknown
rows aren't applied to anything, so there's nothing to test; #26375 is `blocked` on a C++
deploy, so no amount of in-game testing moves it either. That leaves exactly 16 targets.

## Stop 1: Naxxramas 25-man (biggest single stop -- 4 PRs)

Realm: either (Sunstrider has the correct values throughout; Illidan has one known bad value,
see caveat). Requires a level-80 raid group.

1. **Construct Quarter trash** (Patchwork Golem area): confirm Embalming Slime, Patchwork
   Golem, Bile Retcher and Sludge Belcher no longer have the pre-#26822/#26854 immunity/speed
   values -- tests **#26854** and **#26822** together. On Illidan specifically, also confirm
   creature 29356's immunity by hand; the DB shows it landed on the wrong value (-405 instead
   of -93) and this stop is the natural place to see whether that's cosmetic or a real fight
   problem.
2. **Grand Widow Faerlina** (25-man): Mind Control a Naxxramas Worshipper and use Widow's
   Embrace during Frenzy -- tests **#26815**. Sunstrider only; Illidan's Worshipper is still
   immune to MC (not applied there).
3. **Sapphiron** (25-man): kill him and check the loot pool distribution (or `.debug loot
   creature 29991 50`) -- tests **#26751**. Illidan only; Sunstrider's loot is unmodified.

## Stop 2: Howling Fjord (3 PRs, mostly low-level content)

Realm: mixed -- see each line.

4. **Orgrim's Hammer** (Horde starting ship): approach the Scout (entry 32201) and separately
   pull a nearby mob while standing near it -- tests **#26767**, Illidan only. Expect it to
   currently sit on REACT_PASSIVE (never retaliates even if attacked directly), which is the
   PR's *earlier* draft, not its final REACT_DEFENSIVE state -- worth confirming and flagging
   back to the PR author since our tree preserved the stale variant.
5. **Agmar's Hammer / Valgarde**: pick up Rifle the Bodies (11999 Horde / 12000 Alliance)
   without doing the breadcrumb first -- tests **#26204**, Illidan only.
6. **Apothecary Hanes** (`.go c id 23784`): accept Trail of Fire and watch whether Hanes has
   any AI at all -- tests **#26856**, Sunstrider only. Expect this to be BROKEN: `AIName` was
   never set on Sunstrider (see docs/prs/26856.md), so the escort almost certainly won't fire.
   This one is worth testing specifically to convert a data-inferred bug into a confirmed one.

## Stop 3: quick GM-teleport spot checks (no shared walking path -- 9 PRs)

These don't share a zone with anything else worth forcing into a route. Fastest per-PR
verification, in no particular order:

7. **#25981** -- any mage, `.levelup 66`, learn Mage spells, cast Teleport: Stormwind, confirm
   facing on arrival. Both realms.
8. **#26766** -- `.go c 122535`, pull nearby mobs near Vaelen the Flayed, confirm he doesn't
   assist. Both realms.
9. **#26797** -- `.go creature id 27370`, confirm the correct kill-credit NPC behavior for
   Rescue from Town Square. Both realms.
10. **#26798** -- pick up/turn in the quest tied to quest_offer_reward ID 12110 (End of the
    Line, Horde), confirm the reward text and emotes play correctly. Both realms.
11. **#26800** -- `.go c 114439`, watch Bjomolf patrol the sniffed waypoint path. Both realms.
12. **#26709** -- `.go c 6885` area (Kargath Expeditionary Force formation, Blade's Edge
    Mountains, Outland), confirm the patrol formation and pathing look correct. Both realms.
13. **#26784** -- turn in A Righteous Sermon (quest 12321), confirm group completion credits
    correctly for all nearby group members. Both realms.
14. **#26764** -- `.go c 114741` (Sholazar Basin, The Avalanche), confirm Urgreth's out-of-combat
    yells fire and he's no longer drawing/sheathing incorrectly. Both realms.
15. **#26248** -- `.quest add 13281`, `.go c i 31139`, kill Pustulent Horror, confirm Flesh
    Giant Spine drops. Illidan only.

## What this buys

Testing stops 1-2 fully (7 PRs) plus running the 8 quick spot-checks in stop 3 covers all 16
`applied` rows in one session. Stop 1 alone is the highest-density single location (4 PRs).
Expect at least one of these (#26856) to fail outright and #26767 to reveal itself as an
outdated draft rather than a clean pass -- both are useful results, not wasted trips.
