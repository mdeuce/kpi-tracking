# Prompt for a local Claude Code session (Windows PC)

Run Claude Code on the PC that has Path of Building installed, then paste
everything in the block below as the first message.

---

I'm playing Path of Exile 2 (patch 0.5.4, "Return of the Ancients"). I have a
Warrior character, and Path of Building is installed on this Windows PC. You're
running locally, so you can read the PoB files directly.

**Mission 1 — capture current state.**

Find my Path of Building build files. They're usually under one of:

- `%USERPROFILE%\Documents\Path of Building\Builds\*.xml`
- `%USERPROFILE%\Documents\Path of Building (PoE2)\Builds\*.xml`
- `%APPDATA%\Path of Building\Builds\*.xml`

Search rather than assume — the PoE2 community fork picks its own folder. If
you find several builds, show me the list with modified dates and let me pick
the Warrior.

Before you trust the file: check its modified time. If it looks stale, tell me
to open PoB and do **Import/Export Build → Import from website** (account name →
select the Warrior → import tree + items) so we snapshot what I'm actually
wearing rather than an old plan. Wait for me to confirm before continuing.

Then read the build XML and write me a current-state snapshot covering:

- Level, class, ascendancy, number of allocated passives, tree version
- Every skill setup: each socket group, its gems and supports, with level and
  quality, and which ones are disabled
- Every equipped item, by slot, with full mod text — flag empty slots
- PoB's calculated stats: DPS (skill, combined, full), average hit, attack
  speed, crit; life, ES, mana, spirit (total *and* unreserved), armour, evasion,
  block, EHP, max hit taken per damage type; all four resistances with overcap
- The PoB **config flags** the numbers depend on (`enemyIsBoss`, nearby-enemy
  counts, active buffs/charges). Call these out explicitly — a DPS number
  computed against a Pinnacle boss with every condition ticked is not the number
  I see in maps.

Then flag anything obviously wrong before we get to opinions: uncapped
resistances, unspent spirit, empty slots, disabled gems that shouldn't be,
low chaos res, weak EHP for my level.

Save the snapshot to a dated markdown file so we can diff it later.

**Mission 2 — research and recommend.**

Once the snapshot is done, research what's actually working for Warriors in
0.5.4 right now — Titan, Warbringer, and Smith of Kitava — and compare my build
against it. Then recommend improvements **ranked by impact per unit of effort
and currency**, and be concrete: name the passives, the gems, the specific gear
mods to shop for.

I'm open to changing things, including a respec or a different ascendancy, if
you can justify it. But separate the recommendations into:

1. Free / cheap fixes (gem swaps, passive reallocation, config-level mistakes)
2. Moderate investment (targeted gear upgrades)
3. Rebuild-tier changes (ascendancy swap, new main skill)

Don't hand me a generic "best build" writeup — I want the delta between where I
am and where I could be, based on my actual gear and tree.

**Ground rules.**

- Read my real numbers out of the PoB file. Don't estimate or assume.
- If you need me to click something in PoB, tell me exactly what to click.
- If a recommendation depends on a stat you can't see, say so instead of
  guessing.

**Optional — existing work.** I already have a tested PoB parser that turns a
build into this snapshot format. It's in the repo `mdeuce/kpi-tracking`, branch
`claude/poe-warrior-build-analysis-u06s6y`, at `poe-warrior/tools/pob_parse.py`.
It takes a PoB `.xml` build file or an export code directly:

```
python3 poe-warrior/tools/pob_parse.py "path\to\build.xml"
```

Reuse it if it helps, or ignore it and read the XML yourself.
