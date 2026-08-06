# Weeding test plan: the shortest path to the most verified rows

Only the 16 rows with `status: applied` can move to `verified`. Skipped and
unknown rows are not applied anywhere, so there is nothing to test. #26375 is
`blocked` on a C++ deploy, so in-game testing cannot move it either. That leaves
16 targets.

## Stop 1: Naxxramas 25-man

Four PRs. This is the densest single location. Use either realm. Sunstrider has
the correct values throughout. Illidan has one known bad value, described below.
You need a level 80 raid group.

1. **Construct Quarter trash, in the Patchwork Golem area.** Confirm that
   Embalming Slime, Patchwork Golem, Bile Retcher and Sludge Belcher no longer
   hold the immunity and speed values from before #26822 and #26854. This tests
   **#26854** and **#26822** together.

   On Illidan, also check creature 29356's immunity by hand. The database shows
   -405 where it should show -93. Use this stop to find out whether that is
   cosmetic or a real fight problem.

2. **Grand Widow Faerlina, 25-man.** Mind Control a Naxxramas Worshipper, then
   use Widow's Embrace during Frenzy. This tests **#26815**. Sunstrider only:
   Illidan's Worshipper is still immune to Mind Control, because the fix is not
   applied there.

3. **Sapphiron, 25-man.** Kill him and check the loot pool distribution, or run
   `.debug loot creature 29991 50`. This tests **#26751**. Illidan only:
   Sunstrider's loot is unmodified.

## Stop 2: Howling Fjord

Three PRs, mostly low-level content. The realm differs per step.

4. **Orgrim's Hammer, the Horde starting ship.** Approach the Scout, entry
   32201. Then pull a nearby mob while you stand next to it. This tests
   **#26767**, Illidan only.

   Expect REACT_PASSIVE, so the Scout never retaliates even when attacked
   directly. That is the PR's earlier draft, not its final REACT_DEFENSIVE
   state. Our tree kept the stale variant. Confirm it and report it to the PR
   author.

5. **Agmar's Hammer and Valgarde.** Take Rifle the Bodies, quest 11999 for Horde
   or 12000 for Alliance, without doing the breadcrumb first. This tests
   **#26204**, Illidan only.

6. **Apothecary Hanes.** Run `.go c id 23784`, accept Trail of Fire, and watch
   whether Hanes has any AI. This tests **#26856**, Sunstrider only.

   Expect this to fail. `AIName` was never set on Sunstrider, so the escort
   almost certainly does not fire. See `docs/prs/26856.md`. Test it anyway: it
   converts a bug inferred from data into a confirmed one.

## Stop 3: GM teleport spot checks

Nine PRs. These share no zone, so there is no route to plan. Order does not
matter.

7. **#25981.** Take any mage, run `.levelup 66`, learn the Mage spells, and cast
   Teleport: Stormwind. Confirm the facing on arrival. Both realms.
8. **#26766.** Run `.go c 122535`. Pull mobs near Vaelen the Flayed. Confirm he
   does not assist. Both realms.
9. **#26797.** Run `.go creature id 27370`. Confirm the kill-credit NPC behaves
   correctly for Rescue from Town Square. Both realms.
10. **#26798.** Take and turn in the quest attached to quest_offer_reward ID
    12110, End of the Line, Horde. Confirm the reward text and the emotes play.
    Both realms.
11. **#26800.** Run `.go c 114439`. Watch Bjomolf patrol the sniffed waypoint
    path. Both realms.
12. **#26709.** Go to the `.go c 6885` area, the Kargath Expeditionary Force
    formation in Blade's Edge Mountains, Outland. Confirm the formation and the
    pathing. Both realms.
13. **#26784.** Turn in A Righteous Sermon, quest 12321. Confirm every nearby
    group member gets credit. Both realms.
14. **#26764.** Run `.go c 114741`, The Avalanche in Sholazar Basin. Confirm
    Urgreth's out-of-combat yells fire, and that he no longer draws and sheathes
    incorrectly. Both realms.
15. **#26248.** Run `.quest add 13281`, then `.go c i 31139`. Kill Pustulent
    Horror. Confirm the Flesh Giant Spine drops. Illidan only.

## What this covers

Stops 1 and 2 cover 7 PRs. The 9 spot checks in stop 3 cover the rest. Together
they cover all 16 `applied` rows in one session.

Expect #26856 to fail outright, and expect #26767 to show the outdated draft.
Both outcomes are results worth having.
