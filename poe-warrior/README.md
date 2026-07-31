# PoE2 Warrior — build tracking

Companion to the Monk session, for the Warrior character. Two phases:

1. **Capture current state** (this step) — get the live character into Path of
   Building, export it, and turn it into a readable snapshot.
2. **Research and improve** — compare the snapshot against current
   patch-0.5.4 Warrior builds and propose changes.

## Why you have to hand the build over

This session runs in an isolated Linux container in the cloud. It has no access
to your Windows PC, so it cannot read your Path of Building install or your
build files directly. Outbound network access is also restricted, so pobb.in
and pastebin links cannot be fetched from here either. The build has to arrive
as **text you paste into the chat**.

## Step 1 — refresh PoB from the live character

Do this first, otherwise you snapshot whatever you last planned rather than
what you are actually wearing.

1. Open Path of Building (the PoE2 Community fork).
2. **Import/Export Build** → **Import from website**.
3. Enter your account name, pick the Warrior, click **Import**.
4. Import both **passive tree** and **items/skills** when prompted.

## Step 2 — export a share code

1. Still in **Import/Export Build**, look at the **Export** side.
2. Click **Generate** — PoB copies a long base64 code to your clipboard.
3. Paste that code into the chat. It is a few thousand characters; paste all
   of it, and don't let anything trim the ends.

The code contains the whole build: level, ascendancy, passive tree, every gem
and support, every equipped item with full mods, and PoB's own calculated
stats.

## Step 3 — the snapshot gets generated

`tools/pob_parse.py` decodes the code (base64 → zlib → PoB XML) and renders a
markdown snapshot:

```bash
python3 tools/pob_parse.py <code>              # code as an argument
python3 tools/pob_parse.py code.txt            # file containing the code
python3 tools/pob_parse.py build.xml           # a PoB .xml build file
cat code.txt | python3 tools/pob_parse.py -    # stdin
python3 tools/pob_parse.py code.txt --xml raw.xml   # keep the decoded XML too
```

It reports offence, defence, resistances (flagging any that are **uncapped**),
skill setups, equipped gear with full mod text, the PoB config flags the
numbers depend on, and the passive tree URL. Stats it does not recognise are
still printed under "Other stats" so a PoE2 rename never silently drops data.

Snapshots land in `snapshots/`, dated, so build changes stay comparable over
time.

## Alternative: run Claude Code locally instead

If you would rather not paste codes each time, run Claude Code on the Windows
PC itself. It can then read the build files directly and re-snapshot without
you doing anything. PoB keeps them here:

```powershell
Get-ChildItem "$env:USERPROFILE\Documents" -Recurse -Filter *.xml `
  -Path "$env:USERPROFILE\Documents\Path of Building*\Builds" -ErrorAction SilentlyContinue
```

Those `.xml` files feed straight into `pob_parse.py` with no export step.
