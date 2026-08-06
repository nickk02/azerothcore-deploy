# azerothcore-deploy

Deployment state and diagnostic history for the AzerothCore/Playerbots homelab
realms, Illidan and Sunstrider.

This is not a code repository. Nothing builds here.

## Contents

| Path | Holds |
|---|---|
| `worldserver.illidan.conf`, `worldserver.sunstrider.conf` | The live worldserver configs. Database passwords are replaced with `REDACTED_DB_PASSWORD`. |
| `modules/` | The installed module list for each source tree: azerothcore-wotlk and playerbots-wotlk. |
| `filter-gap.py` | Removes the upstream `spell_script_names` and `command` statements from a batch of db_world update files. Run it before you apply that batch to Illidan, which uses an older Playerbots-fork database. |
| `PRIORITY2-DIFF.txt` | A row-level diff between a pre-gap backup and the current Illidan world database. Covers creature_template, conditions, smart_scripts, reference_loot_template and creature. |
| `round2sql-archive/` | The SQL from the round-2 accuracy-fix batch. |
| `BACKUP-MANIFEST.md` | Filenames, sizes, dates and SHA256 values for the backups in `/home/azerothcore/backups` on the deploy VM. The backups are hundreds of megabytes and are not committed. This file is the index. |
| `launcher/` | The news-endpoint scripts, `router.php` and `fetch-news.py`, that serve the launcher's news redirect. |
| `docs/` | Findings, incidents, and per-PR and per-module tracking notes. Start at `docs/README.md`. |
| `ops/vm/` | The VM storage guards. See `ops/vm/README.md`. |
