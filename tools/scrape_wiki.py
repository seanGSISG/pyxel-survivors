"""Mirror the Vampire Survivors wiki pages this clone draws on.

Pulls raw wikitext for every page in the base-game categories (weapons,
evolutions, passives, characters, stages, arcanas, enemies, pickups, ...)
from vampire.survivors.wiki via the MediaWiki API, into wiki/raw/<Category>/.

    uv run tools/scrape_wiki.py            # scrape (skips pages already on disk)
    uv run tools/scrape_wiki.py --list     # print candidate categories + sizes
    uv run tools/scrape_wiki.py --sprites  # download sprite/icon files to wiki/sprites/

Sprites are poncle's copyrighted art: personal local use only, gitignored.
"""

import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://vampire.survivors.wiki/api.php"
ROOT = pathlib.Path(__file__).resolve().parent.parent / "wiki" / "raw"
UA = {"User-Agent": "pyxel-survivors-clone/1.0 (personal fan project)"}

CATEGORIES = [
    "Weapons", "Evolutions", "Unions", "Special weapons", "Passive items",
    "Characters", "Secret characters", "Stages", "Stage mechanics", "Arcanas",
    "Darkanas", "Enemies", "Bosses", "Special Bosses", "Event enemies", "Map events",
    "Pickups", "Relics", "PowerUps", "Gifts", "Merchants", "Item guards",
    "Mechanics", "Gameplay", "Player stats", "Module data",
]
# Listed only (no fetch): used to tag base-game vs DLC content.
TAG_CATEGORIES = ["DLC Content", "Base Game Enemies", "Mad Forest enemies"]


SPRITE_CATEGORIES = [
    "Animated character sprites", "Character sprites", "Animated enemy sprites",
    "Enemy sprites", "Animated light source sprites", "Animated pickup sprites",
    "Animated weapon sprites", "Weapon sprites", "Weapon icons", "Passive item sprites",
    "Pickup sprites", "Arcana sprites", "Arcana icons", "Darkana sprites", "Darkana icons",
    "PowerUp sprites", "PowerUp icons", "Relic sprites", "Relic icons", "Interface images",
    "Map images", "Character select images", "NPC sprites", "Sprites",
]
SPRITES = ROOT.parent / "sprites"


def api(**params):
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"API failed: {url}")


def list_categories():
    out, cont = [], {}
    while True:
        d = api(action="query", list="allcategories", aclimit=500, acprop="size", **cont)
        out += [(c["*"], c.get("pages", 0)) for c in d["query"]["allcategories"]]
        if "continue" not in d:
            return out
        cont = {"accontinue": d["continue"]["accontinue"]}


def members(cat):
    out, cont = [], {}
    while True:
        d = api(action="query", list="categorymembers", cmtitle=f"Category:{cat}",
                cmlimit=500, cmnamespace="0|828", **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def fetch_wikitext(titles):
    """Raw wikitext for up to 50 titles (redirects followed)."""
    d = api(action="query", prop="revisions", rvprop="content", rvslots="main",
            titles="|".join(titles), redirects=1)
    res = {}
    for page in d["query"].get("pages", {}).values():
        revs = page.get("revisions")
        if revs:
            res[page["title"]] = revs[0]["slots"]["main"]["*"]
    return res


def file_members(cat):
    out, cont = [], {}
    while True:
        d = api(action="query", list="categorymembers", cmtitle=f"Category:{cat}",
                cmlimit=500, cmnamespace=6, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def file_urls(titles):
    d = api(action="query", prop="imageinfo", iiprop="url", titles="|".join(titles))
    return {p["title"]: p["imageinfo"][0]["url"]
            for p in d["query"].get("pages", {}).values() if p.get("imageinfo")}


def download_sprites():
    manifest = {}
    for cat in SPRITE_CATEGORIES:
        titles = file_members(cat)
        folder = SPRITES / safe(cat)
        folder.mkdir(parents=True, exist_ok=True)
        got = 0
        for i in range(0, len(titles), 50):
            for title, url in file_urls(titles[i:i + 50]).items():
                name = safe(title.split(":", 1)[1])
                dest = folder / name
                manifest[title] = str(dest.relative_to(SPRITES))
                if dest.exists():
                    continue
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(url, headers=UA)
                        with urllib.request.urlopen(req, timeout=30) as r:
                            dest.write_bytes(r.read())
                        got += 1
                        break
                    except Exception:
                        time.sleep(1 + attempt)
        print(f"{cat:30s} {len(titles):4d} files ({got} downloaded)")
    (SPRITES / "manifest.json").write_text(json.dumps(manifest, indent=1))


def safe(name):
    return re.sub(r"[^\w\-. ]", "_", name).replace(" ", "_")


def main():
    if "--sprites" in sys.argv:
        download_sprites()
        return
    if "--list" in sys.argv:
        for name, n in list_categories():
            if not re.search(r"sprite|icon|track|Crawlers|image|template|update", name, re.I):
                print(f"{n:5d}  {name}")
        return
    index = {}
    for cat in CATEGORIES:
        titles = members(cat)
        index[cat] = titles
        folder = ROOT / safe(cat)
        folder.mkdir(parents=True, exist_ok=True)
        todo = [t for t in titles if not (folder / f"{safe(t)}.wiki").exists()]
        for i in range(0, len(todo), 50):
            for title, text in fetch_wikitext(todo[i:i + 50]).items():
                (folder / f"{safe(title)}.wiki").write_text(text)
            time.sleep(0.5)
        print(f"{cat:20s} {len(titles):4d} pages ({len(todo)} fetched)")
    tags = {cat: members(cat) for cat in TAG_CATEGORIES}
    (ROOT / "index.json").write_text(json.dumps({"categories": index, "tags": tags}, indent=1))


if __name__ == "__main__":
    main()
