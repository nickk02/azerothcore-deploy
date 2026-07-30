# azerothcore-deploy

Deployment state and diagnostic history for the AzerothCore/Playerbots homelab
setup at <homelab-vm-lan-ip> (Illidan/Sunstrider). Not a code repo, no build here.

## Contents

- `worldserver.illidan.conf`, `worldserver.sunstrider.conf` -- live worldserver
  configs, DB passwords redacted to `REDACTED_DB_PASSWORD`.
- `modules/` -- installed module list per source tree (azerothcore-wotlk,
  playerbots-wotlk).
- `filter-gap.py` -- filters the upstream `spell_script_names`/`command`
  statements out of a batch of db_world update files before applying them to
  Illidan's older Playerbots-fork DB.
- `PRIORITY2-DIFF.txt` -- row-level diff of creature_template, conditions,
  smart_scripts, reference_loot_template, and creature between a pre-gap
  backup and the current Illidan world DB.
- `round2sql-archive/` -- SQL from the round-2 accuracy-fix batch.
- `BACKUP-MANIFEST.md` -- filenames, sizes, dates, and sha256 for the backups
  under `/home/azerothcore/backups` on the deploy VM. The backups themselves
  are not committed here (multi-hundred-MB gzips); this is the index.
- `launcher/` -- the news-endpoint scripts (`router.php`, `fetch-news.py`)
  serving the launcher's real-news redirect.
