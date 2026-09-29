"""Parse the mirrored wikitext (wiki/raw) into structured JSON (wiki/data).

Outputs one file per kind: weapons, passives, arcanas, darkanas, characters,
stages (with minute-by-minute wave tables), enemies, pickups, relics,
powerups, map_events. Each record keeps every infobox field (markup
stripped), the page title, a `dlc` flag, and kind-specific extras
(weapon/passive level tables, stage waves).

    uv run tools/parse_wiki.py
"""

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent / "wiki"
RAW, OUT = ROOT / "raw", ROOT / "data"

KINDS = {  # infobox name -> output file
    "Weapon": "weapons", "Passive item": "passives", "Arcana": "arcanas",
    "Character": "characters", "Stage": "stages", "Bestiary": "enemies",
    "Pickup": "pickups", "Relic": "relics", "Powerup": "powerups",
    "Map event": "map_events",
}


# ------------------------------------------------------------ template parse


def find_templates(text, prefix):
    """Yield (start, end, body) of every {{prefix...}} with balanced braces."""
    i = 0
    while True:
        i = text.find("{{" + prefix, i)
        if i < 0:
            return
        depth, j = 0, i
        while j < len(text) - 1:
            two = text[j:j + 2]
            if two == "{{":
                depth += 1
                j += 2
            elif two == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        yield i, j, text[i + 2:j - 2]
        i = j


def split_top(body, sep="|"):
    """Split on `sep` outside nested {{ }} and [[ ]]."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(body):
        two = body[i:i + 2]
        if two in ("{{", "[["):
            depth += 1
            cur.append(two)
            i += 2
            continue
        if two in ("}}", "]]"):
            depth -= 1
            cur.append(two)
            i += 2
            continue
        if body[i] == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(body[i])
        i += 1
    parts.append("".join(cur))
    return parts


def template_params(body):
    parts = split_top(body)
    name = parts[0].strip()
    params, pos = {}, 1
    for p in parts[1:]:
        if "=" in p and not p.lstrip().startswith(("{{", "[[")) or re.match(r"\s*[\w \-]+\s*=", p):
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()
        else:
            params[str(pos)] = p.strip()
            pos += 1
    return name, params


def clean(v):
    """Strip wiki markup to plain text."""
    v = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", v, flags=re.S)
    v = re.sub(r"<br\s*/?>", " / ", v)
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"\[\[File:[^\]]*\]\]", "", v)
    v = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", v)
    for _ in range(3):
        v = re.sub(r"\{\{(?:slink|Slink|Stat|stat|link)\|([^|}]*)(?:\|[^}]*)?\}\}", r"\1", v)
        v = re.sub(r"\{\{(?:Sprite|sprite)\|[^}]*\}\}", "", v)
        v = re.sub(r"\{\{VS\}\}", "Vampire Survivors", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"'''?", "", v)
    return html.unescape(re.sub(r"\s+", " ", v).strip())


def links(v):
    """[[Target|Label]] -> list of (target, label)."""
    return [(a.strip(), (b or a).strip())
            for a, b in re.findall(r"\[\[([^|\]]+)(?:\|([^\]]*))?\]\]", v)
            if not a.startswith("File:")]


# ------------------------------------------------------------ extras


def section(text, title):
    m = re.search(r"^==+\s*" + re.escape(title) + r"\s*==+\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    level = len(re.match(r"=+", m.group(0)).group(0))
    n = re.search(r"^={2,%d}[^=].*$" % level, rest, re.M)
    return rest[:n.start()] if n else rest


def level_table(text):
    """{level: description} from the page's ==Levels== wikitable."""
    out = {}
    for row in table_rows(section(text, "Levels")):
        m = re.match(r"\s*Level\s*(\d+)\s*$", row[0]) if len(row) >= 2 else None
        if m:
            out[int(m.group(1))] = clean(row[1])
    return out


def table_rows(tbl):
    """Rows of a wikitable as lists of raw cell strings."""
    rows = []
    for chunk in re.split(r"^\|-.*$", tbl, flags=re.M)[1:]:
        cells, cur = [], None
        for line in chunk.split("\n"):
            if line.startswith("|}"):
                break
            if line.startswith("!"):
                cur = None
                continue
            if line.startswith("|"):
                if cur is not None:
                    cells.append(cur)
                cur = line[1:]
            elif cur is not None:
                cur += "\n" + line
        if cur is not None:
            cells.append(cur)
        # "a||b" inline cells
        flat = []
        for c in cells:
            flat += split_top(c.replace("||", "\x00"), "\x00")
        # drop leading style="..." attribute segments
        flat = [re.sub(r'^\s*style="[^"]*"\s*\|', "", c) for c in flat]
        if flat:
            rows.append(flat)
    return rows


def waves(text):
    sec = section(text, "Waves")
    out = []
    for row in table_rows(sec):
        if len(row) < 4 or not re.match(r"\s*\d+:\d\d", row[0]):
            continue
        time = row[0].strip()
        enemies = [t for t, _ in links(row[1])]
        rec = dict(time=time, minute=int(time.split(":")[0]), enemies=enemies,
                   enemy_labels=[lbl for _, lbl in links(row[1])],
                   minimum=clean(row[2]), interval=clean(row[3]))
        if len(row) > 4:
            sprite_refs = []
            for _a, _b, body in find_templates(row[4], "Sprite"):
                _, sp = template_params(body)
                sprite_refs.append(sp.get("link") or "sprite:" + sp.get("1", ""))
            rec["bosses"] = sprite_refs or [t for t, _ in links(row[4])]
            rec["treasure"] = [template_params(b)[1] for _, _, b in find_templates(row[4], "treasure")]
        if len(row) > 5:
            rec["events"] = [template_params(b)[1] for _, _, b in find_templates(row[5], "map event")]
        if len(row) > 6:
            rec["notes"] = clean(row[6])
        out.append(rec)
    return out


# ------------------------------------------------------------ main


def main():
    index = json.loads((RAW / "index.json").read_text())
    dlc = set(index["tags"]["DLC Content"])
    base_enemies = set(index["tags"]["Base Game Enemies"])
    results = {v: {} for v in KINDS.values()}
    results["darkanas"] = {}
    seen = set()
    for path in sorted(RAW.rglob("*.wiki")):
        text = path.read_text()
        title_m = None
        for _s, _e, body in find_templates(text, "Infobox "):
            name, params = template_params(body)
            kind = name[len("Infobox "):].strip()
            if kind not in KINDS:
                continue
            out = KINDS[kind]
            if kind == "Arcana" and params.get("type", "").lower().startswith("darkana"):
                out = "darkanas"
            title = path.stem.replace("_", " ")
            title = html.unescape(title)
            title_m = params.get("name") and clean(params["name"]) or title
            key = (out, title_m)
            if key in seen:
                continue
            seen.add(key)
            rec = {k: clean(v) for k, v in params.items()}
            rec["title"] = title_m
            rec["page"] = title
            rec["dlc"] = title in dlc or title_m in dlc
            if out == "enemies":
                rec["base_game"] = title in base_enemies
                rec["variants"] = {}
                for _s2, _e2, sb in find_templates(text, "Statbox Enemy"):
                    _, vp = template_params(sb)
                    vrec = {k: clean(v) for k, v in vp.items()}
                    rec["variants"][vrec.get("title", title)] = vrec
            if out in ("arcanas", "darkanas"):
                rec["affects_list"] = [html.unescape(m.strip()) for m in
                                       re.findall(r"\{\{Sprite\|([^|}]+)", params.get("affects", ""))]
            if out in ("weapons", "passives"):
                rec["levels"] = level_table(text)
            if out == "stages":
                rec["waves"] = waves(text)
            results[out][title_m] = rec
    OUT.mkdir(parents=True, exist_ok=True)
    for name, recs in results.items():
        (OUT / f"{name}.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False))
        n_base = sum(1 for r in recs.values() if not r["dlc"])
        print(f"{name:12s} {len(recs):4d} records ({n_base} base game)")


if __name__ == "__main__":
    main()
