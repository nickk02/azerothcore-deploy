# Deploy docs index

Backfill of everything touched on Sunstrider (upstream realm, `acore_world`) and Illidan
(Playerbots realm, `acore_pb_world`) since 2026-07-28, reconciled against the live databases
and the GitHub API rather than trusted from memory. **The single most important fact in this
table: of the 16 rows marked `applied`, ALL 16 are `verified-in-game: no`.** Nothing has been
confirmed working from an actual game client except the RealmID config-resolution fix (see
docs/incidents/2026-07-30-sunstrider-realmid-config-resolution.md), which isn't a PR at all.

## Counts by status

| status | count |
|---|---|
| applied | 16 |
| skipped | 24 |
| unknown | 6 |
| blocked | 1 |
| already-satisfied | 1 |
| **total** | **48** |

Plus: 2 issues tracked (docs/issues/), 19 modules tracked (docs/modules/, 11 actually installed
-- all on Illidan, none on Sunstrider), 6 findings (docs/findings/), 1 incident
(docs/incidents/).

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
| [26822](prs/26822.md) | Immunities revert (Embalming/Golem/Retcher/Belcher) | sql-only | yes | partial (bad value on 29356) | applied | no |
| [26709](prs/26709.md) | Kargath Expeditionary Force pathing | sql-only | yes | yes | applied | no |
| [26784](prs/26784.md) | Righteous Sermon group completion | sql-only | yes | yes | applied | no |
| [26764](prs/26764.md) | Urgreth of the Thousand Tombs Pt.2 | sql-only | yes | yes | applied | no |
| [26856](prs/26856.md) | Trail of Fire SmartAI rewrite | paired | broken (no AI set) | no | applied | no |
| [26375](prs/26375.md) | Custom spell attributes to DB | paired | SQL only | SQL only | blocked | no |
| [26760](prs/26760.md) | Dead Mage Hunter improvements | sql-only | yes (pre-existing) | yes (pre-existing) | already-satisfied | no |
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
| [26097](prs/26097.md) | (number does not exist upstream) | unknown | -- | -- | unknown | no |
| [26694](prs/26694.md) | (number does not exist upstream) | unknown | -- | -- | unknown | no |
| [26763](prs/26763.md) | Avalanche sub-Zone Pt.1 (Bythius etc.) | sql-only | inconclusive | inconclusive | unknown | no |
| [13322](prs/13322.md) | (number does not exist upstream) | unknown | -- | -- | unknown | no |
| [19679](prs/19679.md) | (number does not exist upstream) | unknown | -- | -- | unknown | no |
| [24380](prs/24380.md) | (number does not exist upstream) | unknown | -- | -- | unknown | no |

## Issues

| # | title | status |
|---|---|---|
| [7014](issues/7014.md) | Winterfall Village Cave death -> Alterac graveyard | open upstream, not investigated |
| [6460](issues/6460.md) | Elwynn Forest missing chest pooling | open upstream, not investigated |

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
- [findings/43-file-union-and-filter.md](findings/43-file-union-and-filter.md)
- [findings/merge-order-lesson-26822-vs-26854.md](findings/merge-order-lesson-26822-vs-26854.md)

## Incidents

- [incidents/2026-07-30-sunstrider-realmid-config-resolution.md](incidents/2026-07-30-sunstrider-realmid-config-resolution.md) -- the only row anywhere in this repo with `verified-in-game: yes`
