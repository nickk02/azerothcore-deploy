-- Issue #26694: heroic "(1)" creature variants are missing pickpocketloot.
-- Copies the pickpocket loot reference from the exact-name-matching
-- normal-mode sibling. MIN() satisfies ONLY_FULL_GROUP_BY; the
-- HAVING COUNT(DISTINCT ...) = 1 guard already guarantees a single value,
-- so ambiguous names (several differently-looted creatures sharing a base
-- name) are excluded rather than guessed at.
UPDATE `creature_template` h
JOIN (
    SELECT h2.entry AS h_entry, MIN(n.pickpocketloot) AS loot_val
    FROM `creature_template` h2
    JOIN `creature_template` n
      ON n.name = TRIM(REPLACE(h2.name, '(1)', ''))
    WHERE h2.name LIKE '% (1)'
      AND h2.pickpocketloot = 0
      AND n.pickpocketloot != 0
      AND n.name NOT LIKE '% (1)'
    GROUP BY h2.entry
    HAVING COUNT(DISTINCT n.pickpocketloot) = 1
) safe ON safe.h_entry = h.entry
SET h.pickpocketloot = safe.loot_val;
