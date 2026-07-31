#!/usr/bin/env python3
"""Decode a Path of Building build and print a readable 'current state' snapshot.

Accepts any of:
  * a PoB export/share code (base64 + zlib, standard or URL-safe alphabet)
  * a path to a PoB build .xml file (Documents\\Path of Building\\Builds\\*.xml)
  * a path to a text file containing an export code

Usage:
    python3 pob_parse.py <code|file>              # markdown snapshot to stdout
    python3 pob_parse.py <code|file> --xml out.xml  # also dump raw build XML
    cat code.txt | python3 pob_parse.py -
"""

from __future__ import annotations

import argparse
import base64
import gzip
import re
import sys
import xml.etree.ElementTree as ET
import zlib

# ---------------------------------------------------------------------------
# decoding
# ---------------------------------------------------------------------------


def _inflate(raw: bytes) -> bytes:
    """PoB uses zlib; be forgiving about raw-deflate and gzip variants."""
    attempts = (
        lambda b: zlib.decompress(b),
        lambda b: zlib.decompress(b, -zlib.MAX_WBITS),
        lambda b: zlib.decompress(b, zlib.MAX_WBITS | 32),
        lambda b: gzip.decompress(b),
    )
    for attempt in attempts:
        try:
            return attempt(raw)
        except Exception:  # noqa: BLE001,S110 - trying every container format
            continue
    raise ValueError(
        "the input decoded as base64 but is not PoB-compressed data. "
        "Make sure you copied the whole code from PoB's "
        "Import/Export Build > Generate, with no characters trimmed."
    )


def decode_code(code: str) -> str:
    """Turn a PoB share code into the build XML."""
    code = code.strip()
    # Tolerate a pasted pobb.in / pastebin URL by taking the trailing segment.
    if code.startswith("http"):
        code = code.rstrip("/").rsplit("/", 1)[-1]
    code = re.sub(r"\s+", "", code)
    # PoB emits URL-safe base64; normalise and re-pad.
    code = code.replace("-", "+").replace("_", "/")
    code += "=" * (-len(code) % 4)
    try:
        raw = base64.b64decode(code, validate=False)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"input is not valid base64: {exc}") from exc
    return _inflate(raw).decode("utf-8", errors="replace")


def load_build(source: str) -> str:
    """Resolve the CLI argument into build XML."""
    if source == "-":
        return decode_code(sys.stdin.read())

    try:
        with open(source, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return decode_code(source)  # not a file, treat as a literal code

    if text.lstrip().startswith("<"):
        return text  # already a PoB .xml build file
    return decode_code(text)


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------

# Stats PoB exposes as <PlayerStat>. Grouped so the snapshot reads top-down
# instead of as an alphabetical dump. Anything not listed still gets printed
# under "Other stats" so a PoE2 rename never silently drops data.
OFFENCE = [
    ("FullDPS", "Full DPS (all sources)"),
    ("CombinedDPS", "Combined DPS"),
    ("TotalDPS", "Skill DPS"),
    ("TotalDot", "Damage over time"),
    ("WithPoisonDPS", "DPS with poison"),
    ("WithBleedDPS", "DPS with bleed"),
    ("WithIgniteDPS", "DPS with ignite"),
    ("AverageDamage", "Average hit"),
    ("Speed", "Attacks/casts per second"),
    ("HitChance", "Hit chance %"),
    ("CritChance", "Crit chance %"),
    ("CritMultiplier", "Crit multiplier"),
    ("AccuracyHitChance", "Accuracy hit chance %"),
]

DEFENCE = [
    ("Life", "Life"),
    ("LifeUnreserved", "Life unreserved"),
    ("LifeUnreservedPercent", "Life unreserved %"),
    ("LifeRegenRecovery", "Life regen /s"),
    ("EnergyShield", "Energy shield"),
    ("EnergyShieldRegenRecovery", "ES regen /s"),
    ("Mana", "Mana"),
    ("ManaUnreserved", "Mana unreserved"),
    ("Spirit", "Spirit"),
    ("SpiritUnreserved", "Spirit unreserved"),
    ("Armour", "Armour"),
    ("PhysicalDamageReduction", "Phys damage reduction %"),
    ("Evasion", "Evasion"),
    ("MeleeEvadeChance", "Melee evade chance %"),
    ("BlockChance", "Block chance %"),
    ("SpellBlockChance", "Spell block chance %"),
    ("SpellSuppressionChance", "Spell suppression %"),
    ("TotalEHP", "Effective HP"),
    ("PhysicalMaximumHitTaken", "Max phys hit taken"),
    ("FireMaximumHitTaken", "Max fire hit taken"),
    ("ColdMaximumHitTaken", "Max cold hit taken"),
    ("LightningMaximumHitTaken", "Max lightning hit taken"),
    ("ChaosMaximumHitTaken", "Max chaos hit taken"),
    ("Str", "Strength"),
    ("Dex", "Dexterity"),
    ("Int", "Intelligence"),
]

RESISTS = [
    ("FireResist", "FireResistOverCap", "Fire"),
    ("ColdResist", "ColdResistOverCap", "Cold"),
    ("LightningResist", "LightningResistOverCap", "Lightning"),
    ("ChaosResist", "ChaosResistOverCap", "Chaos"),
]


def _fmt(value: str) -> str:
    """PoB stores every stat as a float string; render it like the UI does."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if number != number or number in (float("inf"), float("-inf")):
        return str(value)
    if abs(number - round(number)) < 1e-6:
        return f"{int(round(number)):,}"
    if abs(number) >= 100:
        return f"{number:,.0f}"
    return f"{number:,.2f}"


def collect_stats(root: ET.Element) -> dict[str, str]:
    stats: dict[str, str] = {}
    for node in root.iter("PlayerStat"):
        name = node.get("stat")
        if name:
            stats[name] = node.get("value", "")
    return stats


def active_tree(root: ET.Element) -> ET.Element | None:
    tree = root.find("Tree")
    if tree is None:
        return None
    specs = tree.findall("Spec")
    if not specs:
        return None
    active = tree.get("activeSpec")
    if active and active.isdigit():
        index = int(active) - 1
        if 0 <= index < len(specs):
            return specs[index]
    return specs[0]


def active_skills(root: ET.Element) -> list[ET.Element]:
    skills = root.find("Skills")
    if skills is None:
        return []
    sets = skills.findall("SkillSet")
    if not sets:
        return skills.findall("Skill")
    active = skills.get("activeSkillSet")
    chosen = sets[0]
    if active:
        for candidate in sets:
            if candidate.get("id") == active:
                chosen = candidate
                break
    return chosen.findall("Skill")


def equipped_items(root: ET.Element) -> list[tuple[str, ET.Element]]:
    """Return (slot, item) for the active item set, in slot order."""
    items_el = root.find("Items")
    if items_el is None:
        return []
    by_id = {i.get("id"): i for i in items_el.findall("Item")}
    sets = items_el.findall("ItemSet")
    chosen = None
    if sets:
        active = items_el.get("activeItemSet")
        chosen = sets[0]
        if active:
            for candidate in sets:
                if candidate.get("id") == active:
                    chosen = candidate
                    break

    equipped: list[tuple[str, ET.Element]] = []
    if chosen is not None:
        for slot in chosen.findall("Slot"):
            item = by_id.get(slot.get("itemId", ""))
            name = slot.get("name", "?")
            # Slots with itemId="0" are empty.
            if item is not None and slot.get("itemId") not in (None, "0"):
                equipped.append((name, item))
    if not equipped:
        equipped = [("Item", item) for item in items_el.findall("Item")]
    return equipped


def item_lines(item: ET.Element) -> list[str]:
    text = (item.text or "").strip()
    return [line.strip() for line in text.splitlines() if line.strip()]


def item_title(item: ET.Element) -> str:
    lines = item_lines(item)
    rarity = ""
    body: list[str] = []
    for line in lines:
        if line.lower().startswith("rarity:"):
            rarity = line.split(":", 1)[1].strip().title()
            continue
        if ":" in line.split(" ")[0] and line.split(":", 1)[0] in {
            "Unique ID",
            "Item Level",
            "Quality",
            "Sockets",
            "LevelReq",
            "Implicits",
        }:
            continue
        body.append(line)
        if len(body) == 2:
            break
    label = " / ".join(body) if body else "(unnamed)"
    return f"{label}{f'  [{rarity}]' if rarity else ''}"


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def build_report(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    build = root.find("Build")
    stats = collect_stats(root)
    out: list[str] = []
    add = out.append

    cls = build.get("className", "?") if build is not None else "?"
    ascend = build.get("ascendClassName", "") if build is not None else ""
    level = build.get("level", "?") if build is not None else "?"
    spec = active_tree(root)

    add(f"# Current state — {cls}{f' / {ascend}' if ascend and ascend != 'None' else ''}")
    add("")
    add(f"- **Level:** {level}")
    add(f"- **Class / Ascendancy:** {cls} / {ascend or 'none allocated'}")
    if spec is not None:
        nodes = [n for n in (spec.get("nodes") or "").split(",") if n]
        add(f"- **Passives allocated:** {len(nodes)}")
        add(f"- **Tree version:** {spec.get('treeVersion', '?')}")
    if build is not None and build.get("targetVersion"):
        add(f"- **PoB target version:** {build.get('targetVersion')}")

    # --- offence -----------------------------------------------------------
    add("")
    add("## Offence")
    add("")
    shown = _stat_table(add, stats, OFFENCE)

    # --- defence -----------------------------------------------------------
    add("")
    add("## Defence")
    add("")
    shown |= _stat_table(add, stats, DEFENCE)

    # --- resistances -------------------------------------------------------
    add("")
    add("## Resistances")
    add("")
    add("| Element | Current | Over cap | Status |")
    add("| --- | ---: | ---: | --- |")
    for key, over_key, label in RESISTS:
        if key not in stats:
            continue
        shown.add(key)
        shown.add(over_key)
        current = stats.get(key, "")
        over = stats.get(over_key, "")
        try:
            uncapped = float(over) < 0
        except (TypeError, ValueError):
            uncapped = False
        status = "**UNCAPPED**" if uncapped else "capped"
        add(f"| {label} | {_fmt(current)}% | {_fmt(over) if over else '—'} | {status} |")

    # --- skills ------------------------------------------------------------
    add("")
    add("## Skill setups")
    add("")
    skills = active_skills(root)
    if not skills:
        add("_No skills found in the export._")
    for skill in skills:
        slot = skill.get("slot") or skill.get("label") or "Unassigned"
        enabled = skill.get("enabled", "true") == "true"
        gems = skill.findall("Gem")
        if not gems:
            continue
        add(f"**{slot}**{'' if enabled else ' _(disabled)_'}")
        add("")
        for gem in gems:
            name = gem.get("nameSpec") or gem.get("skillId") or "?"
            lvl = gem.get("level", "?")
            qual = gem.get("quality", "0")
            flags = [] if gem.get("enabled", "true") == "true" else ["disabled"]
            suffix = f" _({', '.join(flags)})_" if flags else ""
            add(f"- {name} — level {lvl}, {qual}% quality{suffix}")
        add("")

    # --- gear --------------------------------------------------------------
    add("")
    add("## Equipped gear")
    add("")
    gear = equipped_items(root)
    if not gear:
        add("_No items found in the export._")
    for slot, item in gear:
        add(f"### {slot} — {item_title(item)}")
        add("")
        add("```")
        for line in item_lines(item):
            if line.startswith("Unique ID:"):
                continue
            add(line)
        add("```")
        add("")

    # --- config ------------------------------------------------------------
    config = root.find("Config")
    if config is not None:
        inputs = list(config.findall("Input"))
        if inputs:
            add("## PoB config (what the numbers assume)")
            add("")
            for node in inputs:
                value = (
                    node.get("string")
                    or node.get("number")
                    or node.get("boolean")
                    or ""
                )
                add(f"- `{node.get('name')}` = {value}")
            add("")

    # --- anything we did not explicitly place ------------------------------
    leftovers = sorted(k for k in stats if k not in shown)
    if leftovers:
        add("")
        add("## Other stats reported by PoB")
        add("")
        for key in leftovers:
            add(f"- {key}: {_fmt(stats[key])}")

    if spec is not None:
        url = spec.findtext("URL")
        if url and url.strip():
            add("")
            add("## Passive tree")
            add("")
            add(url.strip())

    return "\n".join(out) + "\n"


def _stat_table(add, stats: dict[str, str], spec: list[tuple[str, str]]) -> set[str]:
    """Emit a two-column table for the stats present; return the keys used."""
    used: set[str] = set()
    rows = [(label, stats[key]) for key, label in spec if key in stats]
    for key, _ in spec:
        if key in stats:
            used.add(key)
    if not rows:
        add("_PoB did not export stats for this section._")
        return used
    add("| Stat | Value |")
    add("| --- | ---: |")
    for label, value in rows:
        add(f"| {label} | {_fmt(value)} |")
    return used


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="PoB export code, .xml build file, or - for stdin")
    parser.add_argument("--xml", help="also write the decoded build XML here")
    args = parser.parse_args()

    try:
        xml_text = load_build(args.source)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.xml:
        with open(args.xml, "w", encoding="utf-8") as handle:
            handle.write(xml_text)

    try:
        print(build_report(xml_text), end="")
    except ET.ParseError as exc:
        print(f"error: decoded data is not valid PoB XML: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
