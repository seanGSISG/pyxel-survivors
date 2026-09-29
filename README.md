# Pyxel Survivors

A Vampire Survivors clone in [Pyxel](https://github.com/kitao/pyxel), driven by data
scraped from the official VS wiki (vampire.survivors.wiki).

```bash
uv run --with pyxel python main.py          # real VS sprites if wiki/atlas exists
uv run --with pyxel python main.py --pixel  # generated 16-colour pixel art
```

Move with arrows / WASD / left stick. Weapons fire on their own. Pause with ESC / P.
Pick a character, a stage and an Arcana, then survive 30 minutes until the Reaper comes.

## What's in it

The "classic core" of the base game, with numbers taken from the wiki:

| | |
|---|---|
| Stages | Mad Forest, Inlaid Library (L-R corridor), Dairy Plant, Gallo Tower (vertical), Cappella Magna, each with its real minute-by-minute wave table (enemy variants, minimums, spawn intervals, bosses, chest odds, map events) |
| Weapons | 28 base weapons + 22 evolutions/unions (Bloody Tear, Vandalier, Phieraggi, Infinite Corridor, Tri-Bracelet...), wiki base stats and per-level gains |
| Passives | all 24 base-game passive items |
| Arcanas | all 22 cards (pick one at the start; Arcana chests at 11:00 / 21:00) |
| Characters | 24 base-game characters with their starting weapons, stats and growth bonuses |
| Enemies | 120 variants with wiki HP / XP / damage / speed / knockback; 22 map-event types (swarms, walls, rushes, stalkers, shooting stars) |
| Systems | XP curve (+600/+2400 at 20/40), gem colours + merge cap, 3/4-option level-ups with owned-item bias, evolution chests (1/3/5 items), light sources and their drop table, Rosary / Orologion / Vacuum / Nduja / chicken, revivals, curse, Reaper at 30:00 |

## Data pipeline

```bash
uv run tools/scrape_wiki.py            # wikitext for ~1,850 pages -> wiki/raw/
uv run tools/scrape_wiki.py --sprites  # ~2,950 sprite/icon files -> wiki/sprites/
uv run tools/parse_wiki.py             # infoboxes, level tables, waves -> wiki/data/*.json
uv run tools/build_gamedata.py         # classic-core selection -> gamedata.json (committed)
uv run --with pillow tools/build_atlas.py  # native-size sprites, shared palette -> wiki/atlas/
```

`wiki/` is gitignored: the sprites are poncle's copyrighted art, fine for a local personal
clone but not for redistribution. Without `wiki/atlas` the game uses its own pixel art.

## Layout

| File | Role |
|---|---|
| `main.py` | App: menus, HUD, stage terrain, rendering |
| `world.py` | simulation: stats, waves, events, combat, pickups, level-ups, chests |
| `weapons.py` | 50 weapon behaviours (update/draw per kind) |
| `arcanas.py` | 22 Arcana effects via hooks |
| `art.py` | wiki atlas vs pixel-art renderer |
| `data.py` | loads `gamedata.json`, engine constants, evolution table |
| `sprites.py`, `icons.py` | generated pixel art |
| `tools/weapon_lab.py` | standalone arena for eyeballing weapons |
| `scenarios/` | headless test entry points (autopilot runs, full 30-min runs per stage, weapon lab, Arcanas) |

Scenarios pass a config to `main.App`: `char`, `stage`, `arcanas`, `minute`, `god`,
`weapons`, `passives`, `level`, `autopilot`, `chest`, `art`. They are built to be driven
headlessly with the pyxel MCP `run` tool.

## Known simplifications

- Gemini adds +1 Amount instead of spawning true counterpart weapons; Game Killer gems
  fire a fireball.
- Gatti Amari cats don't steal pickups; Celestial Dusting doesn't drop hearts.
- Stage terrain is procedural (the wiki has no tilesets); no stage items or coffins.
- No meta-progression (PowerUps, unlocks, gold shop); everything is available from the start.
- The test autopilot plays auto-aim builds well but is poor with the one-sided Whip.

## Credits & licensing

- **Code** (`*.py`, `tools/`, `scenarios/`): MIT, see [LICENSE](LICENSE).
- **`gamedata.json`** is derived from the [Vampire Survivors Wiki](https://vampire.survivors.wiki)
  (stats, level text, wave tables, descriptions) and is licensed
  [CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) like its source.
  Credit goes to the wiki's contributors. Regenerate it with the tools above.
- *Vampire Survivors* and all its names and characters are trademarks of poncle. This is an
  unofficial, non-commercial fan project with no affiliation to or endorsement from poncle.
  No game art is included: the scraper downloads sprites into the gitignored `wiki/` folder
  for local personal use only.
