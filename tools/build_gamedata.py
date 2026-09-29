"""Compile the parsed wiki JSON (wiki/data) into gamedata.json for the game.

Selects the classic-core content (5 main stages, their enemies, ~30 base
weapons with evolutions/unions, all base passives, all Arcanas, the classic
roster) and normalises wiki strings into numbers the engine can use.

    uv run tools/build_gamedata.py
"""

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "wiki" / "data"
RAW = ROOT / "wiki" / "raw"
sys.path.insert(0, str(HERE))

STAGES = ["Mad Forest", "Inlaid Library", "Dairy Plant", "Gallo Tower", "Cappella Magna"]
STAGE_LAYOUT = {"Inlaid Library": "horizontal", "Gallo Tower": "vertical"}
BASE_WEAPONS = [
    "Whip", "Magic Wand", "Knife", "Axe", "Cross", "King Bible", "Fire Wand", "Garlic",
    "Santa Water", "Runetracer", "Lightning Ring", "Pentagram", "Peachone", "Ebony Wings",
    "Phiera Der Tuphello", "Eight The Sparrow", "Gatti Amari", "Song of Mana",
    "Shadow Pinion", "Clock Lancet", "Laurel", "Vento Sacro", "Bone", "Cherry Bomb",
    "Carréllo", "Celestial Dusting", "La Robba", "Bracelet",
]
# Character-exclusive weapons never offered on level-up unless owned.
EXCLUSIVE = {"Bone", "Cherry Bomb", "Carréllo", "Celestial Dusting", "La Robba", "Vento Sacro"}
EVOLVED = [
    "Bloody Tear", "Holy Wand", "Thousand Edge", "Death Spiral", "Heaven Sword",
    "Unholy Vespers", "Hellfire", "Soul Eater", "La Borra", "NO FUTURE", "Thunder Loop",
    "Gorgeous Moon", "Vandalier", "Phieraggi", "Vicious Hunger", "Mannajja",
    "Valkyrie Turner", "Infinite Corridor", "Crimson Shroud", "Fuwalafuwaloo",
    "Bi-Bracelet", "Tri-Bracelet",
]
CHARACTERS = [
    "Antonio Belpaese", "Imelda Belpaese", "Pasqualina Belpaese", "Gennaro Belpaese",
    "Arca Ladonna", "Porta Ladonna", "Lama Ladonna", "Poe Ratcho", "Suor Clerici",
    "Dommario", "Krochi Freetto", "Christine Davain", "Pugnala Provola", "Giovanna Grana",
    "Poppea Pecorina", "Concetta Caciotta", "Mortaccio", "Yatta Cavallo", "Bianca Ramba",
    "O'Sole Meeo", "Sir Ambrojoe", "Iguana Gallo Valletto", "Divano Thelma",
    "Zi Assunta Belpaese",
]


def slug(name):
    s = name.lower().replace("é", "e").replace("ú", "u").replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def num(v, default=None):
    if v is None:
        return default
    m = re.search(r"-?\d[\d,]*\.?\d*", v)
    return float(m.group(0).replace(",", "")) if m else default


def pct(v, default=1.0):
    m = re.match(r"\s*\+?(-?\d[\d,]*\.?\d*)\s*(%?)", v or "")
    if not m:
        return default
    n = float(m.group(1).replace(",", ""))
    return n / 100 if m.group(2) else n


def pierce(v):
    if not v or "Area" in v or "∞" in v:
        return 999
    return int(num(v, 999))


LEVEL_PATTERNS = [
    (r"Fires (\d+) more projectiles?", "amount", 1),
    (r"Base Damage up by ([\d.]+)", "dmg", 1),
    (r"Base Area up by ([\d.]+)%", "area", 0.01),
    (r"Base Speed up by ([\d.]+)%", "speed", 0.01),
    (r"Cooldown reduced by ([\d.]+) seconds?", "cd", -1),
    (r"Effect lasts ([\d.]+) seconds? longer", "dur", 1),
    (r"Passes through (\d+) more enem", "pierce", 1),
    (r"Knockback up by ([\d.]+)%", "kb", 0.01),
    (r"chance.*?up by ([\d.]+)%", "chance", 0.01),
]


def level_delta(desc):
    d = {}
    for pat, key, mul in LEVEL_PATTERNS:
        m = re.search(pat, desc, re.I)
        if m:
            d[key] = round(float(m.group(1)) * mul, 4)
    return d


def weapon_record(name, rec):
    levels = rec.get("levels", {})
    lv_list = [levels[k] for k in sorted(levels, key=int)]
    reqs = [rec[k] for k in ("requires1", "requires2", "requires3") if rec.get(k)]
    out = dict(
        id=slug(name), name=name, type=rec.get("type", "Normal"),
        desc=rec.get("caption") or (lv_list[0] if lv_list else ""),
        rarity=int(num(rec.get("rarity"), 0) or 0),
        max_level=int(num(rec.get("max-level"), len(lv_list) or 1)),
        base=dict(
            dmg=num(rec.get("damage"), 0) or 0,
            cd=num(rec.get("cooldown"), 1.0) or 1.0,
            amount=int(num(rec.get("amount"), 1) or 1) if rec.get("amount") not in ("-", "N/A") else 1,
            pierce=pierce(rec.get("pierce")),
            speed=pct(rec.get("speed")),
            area=pct(rec.get("area")),
            dur=num(rec.get("duration"), 0) or 0,
            interval=num(rec.get("interval"), 0.1) or 0.1,
            kb=num(rec.get("knockback"), 1) or 0,
            pool=int(num(rec.get("pool"), 30) or 30),
            chance=pct(rec.get("chance"), 0) if rec.get("chance") else 0,
            crit=num(rec.get("critMul"), 0) or 0,
        ),
        level_desc=lv_list,
        levels=[level_delta(t) for t in lv_list[1:]],
        evo=None, evo_with=[], union=None, union_with=[], requires=reqs,
        exclusive=name in EXCLUSIVE,
        effects=rec.get("effects", ""),
        image=rec.get("image", ""),
    )
    if rec.get("evolution") and rec["evolution"] in EVOLVED:
        out["evo"] = slug(rec["evolution"])
        items = [rec[k] for k in ("evolution-item", "evolution-item2") if rec.get(k)]
        out["evo_with"] = [slug(i.replace("(item)", "").strip()) for i in items]
    if rec.get("union") and rec["union"] in EVOLVED:
        out["union"] = slug(rec["union"])
        items = [rec[k] for k in ("union-item", "union-item2") if rec.get(k)]
        out["union_with"] = [slug(i) for i in items]
    return out


PASSIVE_STAT = {
    "Might": "might", "Armor": "armor", "Max Health": "maxhp", "Recovery": "recovery",
    "Cooldown": "cooldown", "Area": "area", "Speed": "speed", "Duration": "duration",
    "Amount": "amount", "MoveSpeed": "move", "Move Speed": "move", "Magnet": "magnet",
    "Luck": "luck", "Growth": "growth", "Greed": "greed", "Curse": "curse",
    "Revival": "revival",
}


def passive_record(name, rec):
    stat_raw = rec.get("stat", "")
    stats = [PASSIVE_STAT[s.strip()] for s in re.split(r"[,/]| and ", stat_raw)
             if s.strip() in PASSIVE_STAT]
    per = rec.get("per-level", "")
    val = num(per, 0) or 0
    if "%" in per:
        val /= 100
    return dict(id=slug(name), name=name, stats=stats, per=val,
                max_level=int(num(rec.get("max-level"), 5) or 5),
                rarity=int(num(rec.get("rarity"), 100) or 100),
                desc=rec.get("description", ""), stacking=rec.get("stacking", ""),
                per_text=per, sprite=rec.get("sprite", ""), icon=rec.get("icon", ""))


CHAR_STATS = ["maxhealth", "recovery", "armor", "movespeed", "might", "speed", "duration",
              "area", "cooldown", "amount", "revival", "magnet", "luck", "growth", "greed",
              "curse"]


def char_record(name, rec):
    bonus = {}
    for k in CHAR_STATS:
        v = rec.get(k, "-")
        if v in ("-", "", None) or k == "maxhealth":
            continue
        n = num(v)
        if n is None:
            continue
        bonus[k] = n / 100 if "%" in v else n
    weapons = [w.strip() for w in re.split(r";|,", rec.get("weapon", "")) if w.strip()]
    return dict(id=slug(name), name=name, alias=rec.get("alias") or name.split()[0],
                weapons=[slug(w) for w in weapons], hp=int(num(rec.get("maxhealth"), 100)),
                bonus=bonus, desc=rec.get("description", ""), image=rec.get("image1", ""))


def load_redirects(titles):
    cache_path = RAW / "redirects.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo = [t for t in titles if t not in cache]
    if todo:
        import scrape_wiki
        for i in range(0, len(todo), 50):
            batch = todo[i:i + 50]
            d = scrape_wiki.api(action="query", titles="|".join(batch), redirects=1)
            for r in d["query"].get("redirects", []):
                cache[r["from"]] = r["to"] + ("#" + r["tofragment"] if r.get("tofragment") else "")
            for t in batch:
                cache.setdefault(t, t)
        cache_path.write_text(json.dumps(cache, indent=1))
    return cache


def main():
    load = lambda n: json.loads((DATA / f"{n}.json").read_text())
    weapons_raw, passives_raw = load("weapons"), load("passives")
    enemies_raw, stages_raw = load("enemies"), load("stages")
    chars_raw, arcanas_raw = load("characters"), load("arcanas")

    weapons = {}
    for name in BASE_WEAPONS + EVOLVED:
        weapons[slug(name)] = weapon_record(name, weapons_raw[name])
    passives = {slug(n): passive_record(n, r) for n, r in passives_raw.items() if not r["dlc"]}

    # stages + the enemy variants they reference
    refs = {e for s in STAGES for w in stages_raw[s]["waves"]
            for e in w["enemies"] + w.get("bosses", []) if not e.startswith("sprite:")}
    redirects = load_redirects(sorted(r.split("#")[0] for r in refs))
    variants = {}  # variant title -> (page, record)
    for page, rec in enemies_raw.items():
        for vt, v in rec.get("variants", {}).items():
            variants.setdefault(vt, (page, v))

    enemies, unresolved = {}, []

    by_sprite = {}
    for page, rec in enemies_raw.items():
        for vt, v in rec.get("variants", {}).items():
            img = re.sub(r"^Sprite-|\.png$", "", v.get("image", "")).replace("_", " ")
            by_sprite.setdefault(img, vt)

    def resolve(ref):
        if ref.startswith("sprite:"):
            name = ref[7:].strip()
            ref = by_sprite.get(name, name)
            if ref in variants:
                ref = variants[ref][0] + "#" + ref
        page, _, frag = ref.partition("#")
        target = redirects.get(page, page)
        tpage, _, tfrag = target.partition("#")
        frag = frag or tfrag
        rec = enemies_raw.get(tpage)
        v = None
        if rec:
            vs = rec.get("variants", {})
            v = vs.get(frag) or vs.get(page) or vs.get(tpage) or (next(iter(vs.values())) if vs else None)
            if v is None:
                v = rec
        elif (frag or page) in variants:
            v = variants[frag or page][1]
        if v is None:
            unresolved.append(ref)
            return None
        title = v.get("title") or frag or page
        eid = slug(title)
        if eid not in enemies:
            enemies[eid] = dict(
                id=eid, name=title, page=tpage,
                hp=num(v.get("health"), 10), xp=num(v.get("xp"), 1),
                dmg=num(v.get("damage"), 5), speed=num(v.get("movespeed"), 100),
                kb=num(v.get("knockback"), 1), kb_max=num(v.get("knockback-max"), 3),
                res_freeze=num(v.get("res-freeze"), 0), res_kill=num(v.get("res-kill"), 0),
                hp_level="level" in (v.get("health", "") + v.get("notes", "")).lower(),
                image=v.get("image", ""), skills=v.get("skills", ""),
            )
        return eid

    stages = {}
    for s in STAGES:
        r = stages_raw[s]
        waves = []
        for w in r["waves"]:
            if not re.match(r"\d+:\d\d$", w["time"]):
                continue
            waves.append(dict(
                minute=w["minute"],
                enemies=[e for e in (resolve(x) for x in w["enemies"]) if e],
                bosses=[e for e in (resolve(x) for x in w.get("bosses", [])) if e],
                minimum=int(num(w["minimum"], 10) or 10),
                interval=num(w["interval"], 1.0) or 1.0,
                treasure=w.get("treasure", []),
                events=[dict(name=re.sub(r"\s*\(event\).*|\{\{!\}\}.*", "", e.get("name") or e.get("1", "")),
                             enemy=e.get("enemy", ""), variant=e.get("variant", ""),
                             chance=num(e.get("chance"), 100),
                             repeat=int(num(e.get("repeat"), 1) or 1),
                             amount=int(num(e.get("amount"), 0) or 0),
                             delay=num(e.get("delay"), 0) or 0,
                             duration=num(e.get("duration"), 0) or 0)
                        for e in w.get("events", [])],
            ))
        stages[slug(s)] = dict(
            id=slug(s), name=s, desc=r.get("description", ""),
            layout=STAGE_LAYOUT.get(s, "open"), minutes=int(num(r.get("time"), 30)),
            light_chance=pct(r.get("dchance"), 0.1), light_max=int(num(r.get("dmax"), 10) or 10),
            starting_spawns=int(num(r.get("starting-spawns"), 10) or 10),
            player_speed=num(r.get("player-speed"), 1) or 1,
            enemy_speed=num(r.get("enemy-speed"), 1) or 1,
            waves=waves, image=r.get("image", ""),
        )

    chars = {slug(n): char_record(n, chars_raw[n]) for n in CHARACTERS}
    arcanas = {}
    for n, r in arcanas_raw.items():
        aid = r.get("id", slug(n))
        arcanas[aid] = dict(id=aid, name=n, desc=r.get("description", ""),
                            affects=[slug(a) for a in r.get("affects_list", [])],
                            icon=r.get("icon", ""), image=r.get("image", ""),
                            unlock=r.get("unlock", ""))

    out = dict(weapons=weapons, passives=passives, enemies=enemies, stages=stages,
               characters=chars, arcanas=arcanas,
               pickups={slug(n): r for n, r in load("pickups").items() if not r["dlc"]},
               map_events={slug(n): r for n, r in load("map_events").items()})
    (ROOT / "gamedata.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for k, v in out.items():
        print(f"{k:12s} {len(v)}")
    if unresolved:
        print("UNRESOLVED enemy refs:", sorted(set(unresolved)))


if __name__ == "__main__":
    main()
