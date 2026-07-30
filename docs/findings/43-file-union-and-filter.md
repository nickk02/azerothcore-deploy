# Finding: 43-file db_world union and the spell_script_names/command filter

Illidan's world DB (`acore_pb_world`) was found to be 43 upstream `db_world` update files
behind Sunstrider's (`acore_world`) -- confirmed structurally: the `updates` table on Illidan
stops at `2026_07_16_01.sql` while Sunstrider's continues through `2026_07_24_05.sql` as of
this pass. This reflects the Playerbots fork not having merged upstream past a certain date,
not a bug in either realm.

`filter-gap.py` (in this repo's root) strips any statement targeting the `spell_script_names`
or `command` tables before applying the union to Illidan, because those tables register/bind to
C++ classes or command handlers that don't exist in the older Playerbots-fork binary --
applying them as-is would log "script not found" on every boot.

This union was applied to `acore_pb_world` only. It was deliberately NOT recorded in Illidan's
`updates` table, so a future Playerbots-fork upstream merge will still apply those same files
normally instead of silently skipping them because a name-only match already exists.
