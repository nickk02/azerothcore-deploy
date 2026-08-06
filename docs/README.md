# Deploy docs index

A record of everything changed on Sunstrider (the upstream realm, `acore_world`)
and Illidan (the Playerbots realm, `acore_pb_world`) since 2026-07-28. Every row
was checked against the live databases and the GitHub API. None of it is
recalled from memory.

**Read this first: 20 rows are marked `applied`. All 20 are
`verified-in-game: no`.** Nobody has confirmed any of it from a game client. The
one exception is the RealmID config-resolution fix, which is an incident, not a
PR. See `docs/incidents/2026-07-30-sunstrider-realmid-config-resolution.md`.

## Sweep on 2026-07-30

Checked upstream `azerothcore/azerothcore-wotlk` for PRs merged after #26856
(2026-07-29T08:00:49Z, the latest tracked PR). Nothing had merged since. The most
recent upstream merge was still #26855, already tracked as `skipped` because it
is C++ only.

#26842 was already applied on both realms. It merged on 2026-07-28, before
#26856, and the earlier backfill missed it. It is now tracked as
`already-satisfied`.

Six rows were marked `unknown`: 26097, 26694, 13322, 19679, 24380 and 26763. All
six are now resolved.

Five of the six were never PRs. They are upstream GitHub *issue* numbers, and the
compiled backlog read them as PR numbers. Issues and PRs share one number
sequence on a repository, so the two are easy to confuse.

- #26097 and #26694 have hand-written SQL fixes in the `round2sql-archive/`
  folder of `nickk02/azerothcore-ops`. Database checks confirm both are live on
  both realms. Both are now `applied`.
- #13322, #19679 and #24380 have no fix anywhere. Database checks confirm the
  bugs are still present. All three are now `skipped`.

The sixth, #26763, is a real upstream PR that is still open. An earlier pass
missed it through a bad search. Its SQL is live on both realms, so it is now
`applied`.

Each PR's own document holds the evidence.

## Sweep on 2026-07-31

Checked upstream for anything merged after #26856. Found #26865, merged
2026-07-30. It is a pure-SQL creature and waypoint rewrite with no C++ part.

Before writing, I checked the target GUID range (12804-12810), the waypoint IDs
(128040-128100) and the creature_multispawn rows on both realms. All were free,
and none collided with custom content. The PR is SQL only, so it went to both
realms. After applying it, both realms match the PR's target values exactly.

## Counts by status

| status | count |
|---|---|
| applied | 20 |
| skipped | 27 |
| blocked | 1 |
| already-satisfied | 2 |
| **total** | **50** |

The repository also tracks 10 issues in `docs/issues/`, of which 2 are applied
and 8 are skipped. It tracks 19 modules in `docs/modules/`. Only 11 of those are
installed, all on Illidan and none on Sunstrider. There are 8 findings in
`docs/findings/` and 1 incident in `docs/incidents/`.

## PRs and issues, sorted by status

| # | title | type | sunstrider | illidan | status | verified-in-game |
|---|---|---|---|---|---|---|
| [26767](prs/26767.md) | Orgrim's Hammer Scout attacking players | sql-only | no | stale draft | applied | no |
| [26248](prs/26248.md) | Flesh Giant Spine drop fix | sql-only | no | yes | applied | no |
| [26751](prs/26751.md) | Sapphiron 25 loot pool split | sql-only | no | yes | applied | no |
| [26204](prs/26204.md) | Rifle the Bodies breadcrumb removal | sql-only | no | yes | applied | no |
| [25981](prs/25981.md) | Mage teleport:stormwind orientation | sql-only | yes | yes | applied | no |
| [26766](prs/26766.md) | Vaelen the Flayed attacking NPCs | sql-only | yes | yes | applied | no |
| [26797](prs/26797.md) | Rescue from Town Square quest credit | sql-only | yes | yes | applied | no |
| [26815](prs/26815.md) | Naxx 25 Worshipper MC immunity | sql-only | yes | no | applied | no |
| [26854](prs/26854.md) | Embalming Slime (1) speed/immunity | sql-only | yes | yes | applied | no |
| [26800](prs/26800.md) | Sniff Bjomolf waypoints | sql-only | yes | yes | applied | no |
| [26798](prs/26798.md) | End of the Line (H) reward text/emotes | sql-only | yes | yes | applied | no |
| [26822](prs/26822.md) | Immunities revert (Embalming/Golem/Retcher/Belcher) | sql-only | yes | yes (29356 fixed 2026-07-29) | applied | no |
| [26709](prs/26709.md) | Kargath Expeditionary Force pathing | sql-only | yes | yes | applied | no |
| [26784](prs/26784.md) | Righteous Sermon group completion | sql-only | yes | yes | applied | no |
| [26764](prs/26764.md) | Urgreth of the Thousand Tombs Pt.2 | sql-only | yes | yes | applied | no |
| [26856](prs/26856.md) | Trail of Fire SmartAI rewrite | paired | yes (complete) | no | applied | no |
| [26763](prs/26763.md) | Avalanche sub-Zone Pt.1 (Bythius etc.) | sql-only | yes | yes | applied | no |
| [26865](prs/26865.md) | If Valguarde Falls... sniffed creature data | sql-only | yes | yes | applied | no |
| [26097](prs/26097.md) | Thunderlord Clan Artifacts drop fix (Issue #26097, not a PR) | sql-only | yes | yes | applied | no |
| [26694](prs/26694.md) | Heroic (1) variants missing pickpocket loot (Issue #26694, not a PR) | sql-only | yes | yes | applied | no |
| [26375](prs/26375.md) | Custom spell attributes to DB | paired | SQL only | SQL only | blocked | no |
| [26760](prs/26760.md) | Dead Mage Hunter improvements | sql-only | yes (pre-existing) | yes (pre-existing) | already-satisfied | no |
| [26842](prs/26842.md) | Use Correct Spell for Scalawag Point | sql-only | yes (pre-existing) | yes (pre-existing) | already-satisfied | no |
| [26801](prs/26801.md) | Catch up missed instance resets | cpp-only | no | no | skipped | no |
| [26454](prs/26454.md) | Scarlet Monastery Forgiveness visual | paired | no | no | skipped | no |
| [26810](prs/26810.md) | Sorlof's Booty quest event | paired | no | no | skipped | no |
| [26777](prs/26777.md) | Target Dummy immortality regression | paired | no | no | skipped | no |
| [26855](prs/26855.md) | Hodir Flash Freeze outro | cpp-only | no | no | skipped | no |
| [26806](prs/26806.md) | Supremus Molten Flame chase | cpp-only | no | no | skipped | no |
| [26789](prs/26789.md) | Skeram aggro yell gendered text | cpp-only | no | no | skipped | no |
| [26802](prs/26802.md) | Skeram aggro yell build fix | cpp-only | no | no | skipped | no |
| [26781](prs/26781.md) | Yogg-Saron reset recovery | cpp-only | no | no | skipped | no |
| [26684](prs/26684.md) | Algalon defeat/wipe/pathfinding | cpp-only | no | no | skipped | no |
| [26666](prs/26666.md) | Magmus Fiery Burst/War Stomp IDs | cpp-only | no | no | skipped | no |
| [26439](prs/26439.md) | Higher Learning pooled respawn | paired | no | no | skipped | no |
| [26761](prs/26761.md) | Feral Defender melee damage | sql-only | no | no | skipped | no |
| [26841](prs/26841.md) | Mimiron Rocket Strike combat log | cpp-only | no | no | skipped | no |
| [26844](prs/26844.md) | Mimiron Rocket Strike timing sync | paired | no | no | skipped | no |
| [26796](prs/26796.md) | SAI ranged melee-state regression | cpp-only | no | no | skipped | no |
| [26825](prs/26825.md) | Restore additional player saves | cpp-only | no | no | skipped | no |
| [26823](prs/26823.md) | Revert DB-only-PR CI skip | cpp-only (CI) | n/a | n/a | skipped | no |
| [26770](prs/26770.md) | Naxx boss summon despawn cleanup | cpp-only | no | no | skipped | no |
| [24340](prs/24340.md) | ICC Blood Orb gameobject | paired | no | no | skipped | no |
| [26813](prs/26813.md) | Shade of Akama evade crash fix | cpp-only | no | no | skipped | no |
| [26539](prs/26539.md) | SAI SetFollow speed inheritance | cpp-only | no | no | skipped | no |
| [26843](prs/26843.md) | Abdul the Insane creatures | sql-only | no (unconfirmed) | no (unconfirmed) | skipped | no |
| [26292](prs/26292.md) | Ursal the Mauler druids freed | sql-only | no | no | skipped | no |
| [13322](prs/13322.md) | Lake Snappers missing from Lake Elrendar (Issue #13322, not a PR) | issue-only | no | no | skipped | no |
| [19679](prs/19679.md) | Bloodmyst Isle bridge trigger missing (Issue #19679, not a PR) | issue-only | no | no | skipped | no |
| [24380](prs/24380.md) | Call to Arms Alliance flags in Dalaran (Issue #24380, not a PR) | issue-only | no | no | skipped | no |

## Issues

| # | title | status |
|---|---|---|
| [16313](issues/16313.md) | Missing Spanish text for Mountaineer Stormpike | applied |
| [7956](issues/7956.md) | Desolace hyenas missing patrol | applied |
| [7014](issues/7014.md) | Winterfall Village Cave death -> Alterac graveyard | skipped -- not a DB fix (map/vmap zone geometry) |
| [6460](issues/6460.md) | Elwynn Forest missing chest pooling | skipped -- no concrete fix in thread |
| [16312](issues/16312.md) | Missing Spanish text for Mebok Mizzyrix | skipped -- no fix in thread despite label |
| [20821](issues/20821.md) | No Wisps at Hidden Shrine in Ashenvale | skipped -- proposed fix contradicted in thread |
| [20820](issues/20820.md) | Blade's Edge Mountains post-2.1 revamp | skipped -- no fix in thread |
| [23092](issues/23092.md) | Quest 12818 Clean Up gameobject spawns incomplete | skipped -- author retracted fix as unimplementable |
| [8507](issues/8507.md) | Western Plaguelands Blood of Heroes spawns | skipped -- fix in wrong DB schema (cmangos) |
| [14209](issues/14209.md) | Missing quest_template_locale entries (bulk) | skipped -- data dump too broad for this pass |

## Modules

11 of 19 tracked modules are actually installed, all on Illidan (Playerbots realm), none on
Sunstrider: [ah-bot-plus](modules/ah-bot-plus.md), [aoe-loot](modules/aoe-loot.md),
[assistant](modules/assistant.md), [autobalance](modules/autobalance.md),
[dungeon-clear](modules/dungeon-clear.md), [learn-spells](modules/learn-spells.md),
[multibot-bridge](modules/multibot-bridge.md),
[player-bot-level-brackets](modules/player-bot-level-brackets.md),
[quest-helper](modules/quest-helper.md), [solo-lfg](modules/solo-lfg.md),
[transmog](modules/transmog.md).

8 tracked modules were not found installed on either realm's module tree as of 2026-07-29:
[junk-to-gold](modules/junk-to-gold.md), [solocraft](modules/solocraft.md),
[individual-progression](modules/individual-progression.md), [ale-eluna](modules/ale-eluna.md),
[fly-anywhere](modules/fly-anywhere.md), [item-level-up](modules/item-level-up.md),
[dynamic-xp](modules/dynamic-xp.md), [weekend-xp](modules/weekend-xp.md).

## Findings

- [findings/cpp-deploys.md](findings/cpp-deploys.md) -- the eleven PRs compiled into Sunstrider's live binary, none tested in-game
- [findings/instancesavemgr-day-alignment-bug.md](findings/instancesavemgr-day-alignment-bug.md)
- [findings/cmake-install-prefix-config-trap.md](findings/cmake-install-prefix-config-trap.md)
- [findings/illidan-segfaults-playerbots-hypothesis.md](findings/illidan-segfaults-playerbots-hypothesis.md)
- [findings/illidan-crash-3-gameevent-visit-segfault.md](findings/illidan-crash-3-gameevent-visit-segfault.md) -- third Illidan segfault, first one with a backtrace; plausible mechanism in `GameEventAIHookWorker::Visit`, not confirmed
- [findings/gameevent-visit-iterator-invalidation-fix.md](findings/gameevent-visit-iterator-invalidation-fix.md) -- the fix for the above, built and **live on Sunstrider only**, not on Illidan. Also corrects the upstream citation: TrinityCore#17587 is closed (stale, not fixed); only #26687 is open.
- [findings/illidan-crash-4-mod-assistant-double-delete.md](findings/illidan-crash-4-mod-assistant-double-delete.md) -- **confirmed root cause** of the shutdown crash: `mod-assistant`'s `Assistant` derives from two script bases and is deleted twice by `ScriptMgr::Unload()`. Supersedes the earlier OpenSSL/DB-pool explanations, which were both wrong. No data risk.
- [findings/mmap-version-mismatch-investigation.md](findings/mmap-version-mismatch-investigation.md) -- generator v20/v19 mismatch is pervasive (44.6% of tiles) but memory-safe by code inspection; not a plausible direct segfault cause
- [findings/43-file-union-and-filter.md](findings/43-file-union-and-filter.md)
- [findings/merge-order-lesson-26822-vs-26854.md](findings/merge-order-lesson-26822-vs-26854.md)

## Ops

- [ops/vm-storage-guards.md](ops/vm-storage-guards.md) -- coredump store cap, on-disk scratch dir, tmpfs age-out, and the `ac-diskguard` threshold timer, added after `/tmp` (a tmpfs) hit 100% full. Config files themselves live in [../ops/vm/](../ops/vm/).

## Incidents

- [incidents/2026-07-30-sunstrider-realmid-config-resolution.md](incidents/2026-07-30-sunstrider-realmid-config-resolution.md) -- the only row anywhere in this repo with `verified-in-game: yes`
