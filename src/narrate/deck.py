"""Build a self-contained slides page from a deck source (`narrate build-deck`).

A talk folder holds:

  slides.html           the source: the slides in <div id="stage">, one element
                        per slide with the class `slide`, and the page's own style
  notes/slide_NN.md     the narration, one file per slide (NN from 01)

In the source:

  \\( ... \\)        inline TeX, typeset as an inline SVG
  \\[ ... \\]        display TeX, typeset as a centred SVG block
  src="asset:F"    an image, embedded as a data URI from the assets folder
  data-nofoot      on a slide: no footer line

Every other slide gets a footer `<p class="foot">FOOT · k / N</p>` before its
closing tag. The notes fill `const NOTES = [...]`.

A source with no frame of its own (no `<div id="notes"`) gets narrate's frame:
frame/frame.css as a style before the source's first style (so the source can
override it), and frame/frame.html (notes panel, bar, navigation script) after
the stage. A source with its own frame keeps it and must contain
`const NOTES = [];`, which is filled.

Formulas are typeset by tex_svg.mjs with MathJax from the project's
node_modules (`npm install mathjax-full`), so the page needs no script, font or
stylesheet from elsewhere for its mathematics. TeX macros come from a JSON file
({"name": "body"} or {"name": ["body", number of arguments]}).

From billpage/oziewicz src/narration/build_deck.py (2026-11-17): output path,
macros and node lookup made settings; slides found by class token; the frame.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
MATH = re.compile(r"\\\((.+?)\\\)|\\\[(.+?)\\\]", re.S)
OPEN = re.compile(r"<(\w+)\b([^>]*)>")
CLASS = re.compile(r"""\bclass\s*=\s*(["'])(.*?)\1""", re.S)


class DeckError(Exception):
    pass


def is_slide(attrs: str) -> bool:
    m = CLASS.search(attrs)
    return bool(m) and "slide" in m.group(2).split()


def node_base(starts) -> Path:
    """The first folder, from each start upwards, that holds node_modules/mathjax-full."""
    for start in starts:
        for d in [start, *start.parents]:
            if (d / "node_modules" / "mathjax-full").is_dir():
                return d
    raise DeckError("mathjax-full not found: run `npm install mathjax-full` in the project")


def typeset(stage: str, macros: dict, base: Path) -> str:
    """Replace every \\( \\) and \\[ \\] in the stage by MathJax SVG."""
    found = list(MATH.finditer(stage))
    if not found:
        return stage
    items = [{"tex": (m.group(1) or m.group(2)).strip(), "display": m.group(2) is not None} for m in found]
    if shutil.which("node") is None:
        raise DeckError("node is needed to typeset TeX (sudo apt install nodejs)")
    res = subprocess.run(["node", str(HERE / "tex_svg.mjs")],
                         input=json.dumps({"macros": macros, "items": items}),
                         capture_output=True, text=True, timeout=300,
                         env={**__import__("os").environ, "NARRATE_NODE_BASE": str(base)})
    if res.returncode != 0:
        raise DeckError(res.stderr.strip())
    svgs = json.loads(res.stdout)
    out, last = [], 0
    for m, it, svg in zip(found, items, svgs):
        out.append(stage[last:m.start()])
        out.append(f'<div class="mathd">{svg}</div>' if it["display"] else f'<span class="math">{svg}</span>')
        last = m.end()
    out.append(stage[last:])
    return "".join(out)


def embed_assets(stage: str, assets: Path | None) -> str:
    def repl(m):
        if assets is None:
            raise DeckError(f"asset {m.group(1)} used but no assets folder given (--assets)")
        f = assets / m.group(1)
        if not f.is_file():
            raise DeckError(f"asset not found: {f}")
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return f'src="data:{mime};base64,{base64.b64encode(f.read_bytes()).decode()}"'
    return re.sub(r'src="asset:([^"]+)"', repl, stage)


def slide_spans(stage: str):
    """(start of the closing tag, attributes) of each element whose class list
    contains `slide`, in order; nested elements of the same name are counted."""
    spans, pos = [], 0
    for m in OPEN.finditer(stage):
        if m.start() < pos or not is_slide(m.group(2)):
            continue
        tag, depth, i = m.group(1), 1, m.end()
        tags = re.compile(rf"<(/?){tag}\b[^>]*>", re.I)
        while depth:
            t = tags.search(stage, i)
            if t is None:
                raise DeckError(f"no closing </{tag}> for a slide")
            depth += -1 if t.group(1) else 1
            i = t.end()
        spans.append((t.start(), m.group(2)))
        pos = i
    return spans


def add_footers(stage: str, foot: str) -> tuple[str, int]:
    """Add a footer to each slide without data-nofoot; return the stage and the number of slides."""
    spans = slide_spans(stage)
    n = len(spans)
    for k, (close, attrs) in reversed(list(enumerate(spans, 1))):
        if "data-nofoot" not in attrs:
            stage = stage[:close] + f'<p class="foot">{foot} · {k} / {n}</p>\n' + stage[close:]
    return stage, n


def build(talk: Path, out: Path, *, assets: Path | None = None, foot: str = "",
          macros: dict | None = None, node_starts=()) -> dict:
    src_file = talk / "slides.html"
    if not src_file.is_file():
        raise DeckError(f"{src_file} not found")
    src = src_file.read_text(encoding="utf-8")
    if '<div id="stage">' not in src:
        raise DeckError(f'{src_file} has no <div id="stage">')
    a = src.index('<div id="stage">')
    own_frame = '<div id="notes"' in src[a:]
    if own_frame:
        b = src.index('<div id="notes"', a)
        rest = src[b:]
        if "const NOTES = [];" not in rest:
            raise DeckError(f"{src_file} has its own frame, so it must contain `const NOTES = [];`")
        head = src[:a]
    else:
        if "</head>" not in src[:a] or "</body>" not in src[a:]:
            raise DeckError(f"{src_file} needs a <head> and a </body>")
        b = src.rindex("</body>")
        frame_css = (HERE / "frame" / "frame.css").read_text(encoding="utf-8")
        frame_html = (HERE / "frame" / "frame.html").read_text(encoding="utf-8")
        frame_html = frame_html[frame_html.index("-->") + 4:]           # drop the file's own comment
        h = src.index("<style") if "<style" in src[:a] else src.index("</head>")
        head = src[:h] + "<style>\n" + frame_css + "</style>\n" + src[h:a]
        rest = frame_html + src[b:]

    stage, n = add_footers(src[a:b], foot)
    if n == 0:
        raise DeckError(f"{src_file}: no element with the class `slide` in the stage")
    base = node_base([*node_starts, talk.resolve()]) if MATH.search(stage) else None
    stage = embed_assets(typeset(stage, macros or {}, base) if base else stage, assets)

    notes, missing = [], []
    for k in range(1, n + 1):
        f = talk / "notes" / f"slide_{k:02d}.md"
        notes.append(f.read_text(encoding="utf-8").strip() if f.exists() else "")
        if not f.exists():
            missing.append(k)
    rest = rest.replace("const NOTES = [];", "const NOTES = " + json.dumps(notes, ensure_ascii=False)
                        .replace("</", "<\\/") + ";", 1)
    page = head + stage + rest
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    words = sum(len(t.split()) for t in notes)
    return {"out": out, "slides": n, "with_notes": sum(bool(t) for t in notes), "words": words,
            "mb": len(page.encode("utf-8")) / 1e6, "own_frame": own_frame, "missing": missing}
