"""Build the browser version: dist/index.html (Pyxel WASM, one self-contained page).

    uv run --with pyxel tools/build_web.py           # the game
    uv run --with pyxel tools/build_web.py --bench   # minute-15 autopilot, fps in the tab title

Packages from a clean `git archive HEAD` export, never the working tree, so the
local wiki/ sprites can't leak into the public build. Only the game modules,
gamedata.json and themes/ go into the .pyxapp.
"""

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
REPO = "https://github.com/seanGSISG/pyxel-survivors"
SHARE_IMG = "https://raw.githubusercontent.com/seanGSISG/pyxel-survivors/main/docs/media/stage_library.png"

HEAD = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pyxel Survivors: play in your browser</title>
<meta name="description" content="A Vampire Survivors tribute in Python/Pyxel with an original 90s theme. 5 stages, 50 weapons, 22 Arcanas. Free, no install.">
<meta property="og:title" content="Pyxel Survivors">
<meta property="og:description" content="Survive 30 minutes against pizza bats, VHS ghosts and a video-store Reaper. Free in your browser.">
<meta property="og:image" content="{SHARE_IMG}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><rect width='16' height='16' fill='%231a1033'/><text x='8' y='13' font-size='12' text-anchor='middle'>🍕</text></svg>">
<style>html,body{{margin:0;background:#1a1033}}</style>
</head>
<body>
"""


def export(dst):
    """Committed files at HEAD, extracted into dst."""
    blob = subprocess.run(["git", "-C", str(ROOT), "archive", "HEAD"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        tar.extractall(dst, filter="data")


def main():
    bench = "--bench" in sys.argv
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        src, app = tmp / "src", tmp / "pyxel_survivors"
        export(src)
        app.mkdir()
        for f in src.glob("*.py"):
            shutil.copy(f, app)
        shutil.copy(src / "gamedata.json", app)
        shutil.copytree(src / "themes", app / "themes")
        startup = "main.py"
        if bench:
            shutil.copy(ROOT / "tools" / "web_bench.py", app / "bench.py")
            startup = "bench.py"
        leaked = [p for p in app.rglob("*") if "wiki" in p.parts]
        if leaked:
            sys.exit(f"refusing to build: wiki/ content in the app: {leaked[:3]}")
        subprocess.run(["pyxel", "package", str(app), str(app / startup)], cwd=tmp, check=True,
                       capture_output=True)
        subprocess.run(["pyxel", "app2html", "pyxel_survivors.pyxapp"], cwd=tmp, check=True,
                       capture_output=True)
        page = (tmp / "pyxel_survivors.html").read_text()
    body = page.removeprefix("<!doctype html>").strip()
    DIST.mkdir(exist_ok=True)
    out = DIST / ("bench.html" if bench else "index.html")
    out.write_text(HEAD + body + "\n</body>\n</html>\n")
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
