"""narrate - render and publish narrated slide pages with a project's settings.

    narrate config                      show the settings found for this directory
    narrate render SLIDES.html [voiceover options]   (folder: <narration_dir>/<--name or deck name>)
    narrate publish PAGE_narrated.html [--no-dispatch]
    narrate build-deck TALK_FOLDER [--name N] [--foot TEXT] [--assets DIR] [--macros FILE] [--out FILE]

Settings come from `narration.toml`, looked for in the current directory and
its parents; the directory that holds it is the project root, and relative
paths in it are relative to that root. Without the file, `render` uses
voiceover's own defaults with narrate's common terms, and `publish` refuses.

    repo = "owner/name"                    # GitHub repository (for publish)
    narration_dir = "~/name-narration"     # renders go to <narration_dir>/<--name, or deck name>/
    output_worktree = "~/name-output"      # a worktree of the output branch (for publish)
    output_branch = "output"
    published_dir = "narrated"             # folder on the output branch
    pages_workflow = "pages.yml"
    terms = ["path/to/terms.json"]         # project pronunciations
    package_terms = true                   # include narrate's common terms
    hash_list = "talks/narrated.sha256"    # publish gate; leave out for none

    [deck]                                 # for build-deck; the command line wins
    macros = "src/narration/tex_macros.json"   # TeX macros, {"name": "body" or ["body", nargs]}
    assets = "~/name-output/figures"       # where src="asset:F" images are found

    [voice]                                # voiceover options; the command line wins
    tts = "edge"
    voice = "en-CA-LiamNeural"
    pause = 30
    rate = "+0%"
    reencode = 32                          # the only one kept when the command line picks another --tts

Pronunciations come in three layers, merged with a later layer winning on the
same key: narrate's `terms/common.json` < the project's `terms` files (in order)
< the talk's `pronunciations.json` beside the slides page < a file given with
--pronunciations. The merged table is written to <outdir>/<name>_terms.json and
given to voiceover, which applies it longest key first.

Publishing with a hash gate (`hash_list` set) pushes the page to the output
branch and writes its SHA-256 line into the hash list in the project's working
copy, for a pull request to main. The Pages workflow is not started: merging
that pull request starts it, and the gate fails the build until the new hash is
on main. Without a gate the workflow is started (with `gh`, if signed in).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

CONFIG = "narration.toml"
PACKAGE_TERMS = Path(__file__).with_name("terms") / "common.json"
KNOWN = {"repo", "narration_dir", "output_worktree", "output_branch", "published_dir",
         "pages_workflow", "terms", "package_terms", "hash_list", "voice", "deck"}
KNOWN_VOICE = {"tts", "voice", "pause", "reencode", "rate"}
KNOWN_DECK = {"macros", "assets"}


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------
def find_config(start: Path):
    for d in [start, *start.parents]:
        if (d / CONFIG).is_file():
            return d / CONFIG
    return None


def load_settings(start: Path | None = None):
    path = find_config((start or Path.cwd()).resolve())
    data = {}
    if path:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
        unknown = set(data) - KNOWN
        unknown |= {f"voice.{k}" for k in set(data.get("voice", {})) - KNOWN_VOICE}
        unknown |= {f"deck.{k}" for k in set(data.get("deck", {})) - KNOWN_DECK}
        if unknown:
            die(f"{path}: unknown setting(s): {', '.join(sorted(unknown))}")
    root = path.parent if path else None
    name = data.get("repo", "").split("/")[-1] or None

    def where(value):
        if value is None:
            return None
        p = Path(os.path.expanduser(value))
        return p if p.is_absolute() or root is None else root / p

    return {
        "config": path,
        "root": root,
        "repo": data.get("repo"),
        "narration_dir": where(data.get("narration_dir")) or (Path.home() / f"{name}-narration" if name else None),
        "output_worktree": where(data.get("output_worktree")) or (Path.home() / f"{name}-output" if name else None),
        "output_branch": data.get("output_branch", "output"),
        "published_dir": data.get("published_dir", "narrated"),
        "pages_workflow": data.get("pages_workflow", "pages.yml"),
        "terms": [where(t) for t in data.get("terms", [])],
        "package_terms": data.get("package_terms", True),
        "hash_list": where(data.get("hash_list")),
        "voice": data.get("voice", {}),
        "deck_macros": where(data.get("deck", {}).get("macros")),
        "deck_assets": where(data.get("deck", {}).get("assets")),
    }


def pages_url(repo, published_dir, filename):
    owner, name = repo.split("/")
    return f"https://{owner}.github.io/{name}/{published_dir}/{filename}"


# --------------------------------------------------------------------------
# pronunciations
# --------------------------------------------------------------------------
def term_layers(settings, slides: Path, extra: str | None):
    layers = []
    if settings["package_terms"]:
        layers.append(("package", PACKAGE_TERMS))
    layers += [("project", p) for p in settings["terms"]]
    talk = slides.parent / "pronunciations.json"
    if talk.is_file():
        layers.append(("talk", talk))
    if extra:
        layers.append(("command line", Path(extra).expanduser()))
    return layers


def merge_terms(layers):
    merged, source = {}, {}
    for kind, path in layers:
        if not path.is_file():
            die(f"pronunciation file not found ({kind} layer): {path}")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            die(f"{path}: expected a JSON object {{written: spoken}}")
        for k, v in data.items():
            merged[k] = v
            source[k] = kind
    return merged, source


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_config(args):
    s = load_settings()
    if not s["config"]:
        print(f"no {CONFIG} in {Path.cwd()} or its parents; render uses the package defaults")
    for k, v in s.items():
        if k == "terms":
            v = [str(p) for p in v]
        print(f"{k:16s} {v}")


def option_value(rest, name):
    """The value given for option `name` in the pass-through arguments, or None."""
    for i, a in enumerate(rest):
        if a == name:
            return rest[i + 1] if i + 1 < len(rest) else ""
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def cmd_render(args, rest):
    slides = Path(args.slides).expanduser()
    if not slides.is_file():
        die(f"{slides} not found")
    s = load_settings()
    name = option_value(rest, "--name") or slides.stem     # voiceover names its files so too
    if args.outdir:
        outdir = Path(args.outdir).expanduser()
    elif s["narration_dir"]:
        outdir = s["narration_dir"] / name
    else:
        outdir = Path.cwd() / f"{name}_narration"
    outdir.mkdir(parents=True, exist_ok=True)

    layers = term_layers(s, slides, args.pronunciations)
    merged, source = merge_terms(layers)
    terms_file = outdir / f"{name}_terms.json"
    terms_file.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts = {}
    for kind in source.values():
        counts[kind] = counts.get(kind, 0) + 1
    print("terms  : " + "; ".join(f"{kind} {p} ({counts.get(kind, 0)} kept)" for kind, p in layers)
          + f"  ->  {terms_file} ({len(merged)} entries)")

    voice = dict(s["voice"])
    cmd = [sys.executable, "-u", "-m", "narrate.voiceover", str(slides), "-d", str(outdir)]
    given_tts = option_value(rest, "--tts")
    if given_tts and given_tts != voice.get("tts", "edge"):
        voice = {k: v for k, v in voice.items() if k == "reencode"}   # another back-end: its own defaults
    for key in ("tts", "voice", "pause", "rate", "reencode"):
        if key in voice and not option_value(rest, f"--{key}"):
            cmd += [f"--{key}", str(voice[key])]
    cmd += ["--pronunciations", str(terms_file)] + rest
    if ("reencode" in voice or option_value(rest, "--reencode")) and shutil.which("ffmpeg") is None:
        die("ffmpeg is needed for --reencode (sudo apt install ffmpeg)")
    print("run    : voiceover " + " ".join(shlex.quote(c) for c in cmd[4:]), flush=True)
    if args.dry_run:
        return
    code = subprocess.call(cmd)
    page = outdir / f"{name}_narrated.html"
    if code == 0 and page.exists() and "--preview" not in rest:
        print(f"\nOpen {page} in a browser to check it; publish with\n  narrate publish {page}")
    sys.exit(code)


def check_page(page: Path):
    if not page.is_file():
        die(f"{page} not found")
    if not page.name.endswith("_narrated.html"):
        die("expected a *_narrated.html page from voiceover")
    text = page.read_text(encoding="utf-8", errors="replace")
    if 'id="nv-audio"' not in text:
        die(f"{page} is not a narrated page")
    if "const MISSING = [];" not in text:
        die(f"some slides in {page} have no audio; run narrate render again to fill them in")
    if re.search(r"\bEMBEDDED = false\b", text):     # in `const SW = .., SH = .., EMBEDDED = ..`
        die("this page links its audio (--link); publish the embedded version")
    mb = page.stat().st_size / 1e6
    if mb >= 95:
        die(f"{page} is {mb:.0f} MB; GitHub refuses files over 100 MB (render with --reencode 24)")
    if mb >= 50:
        print(f"warning: {page} is {mb:.0f} MB; consider --reencode 32 to keep the output branch small")


def git(worktree, *a, capture=False):
    r = subprocess.run(["git", "-C", str(worktree), *a], text=True,
                       stdout=subprocess.PIPE if capture else None)
    if r.returncode:
        die(f"git {' '.join(a)} failed in {worktree}")
    return (r.stdout or "").strip()


def update_hash_list(hash_list: Path, line_hash: str, filename: str):
    lines = hash_list.read_text(encoding="utf-8").splitlines() if hash_list.exists() else []
    new = f"{line_hash}  {filename}"
    kept = [ln for ln in lines if ln.split()[-1:] != [filename]]
    changed = new not in lines
    if changed:
        hash_list.parent.mkdir(parents=True, exist_ok=True)
        hash_list.write_text("\n".join(kept + [new]) + "\n", encoding="utf-8")
    return new, changed, len(kept) < len(lines)


def cmd_publish(args):
    page = Path(args.page).expanduser()
    check_page(page)
    s = load_settings()
    if not s["config"]:
        die(f"no {CONFIG} found; publish needs the repository and its output worktree")
    if not s["repo"]:
        die(f"{s['config']}: set repo = \"owner/name\"")
    out = s["output_worktree"]
    if not (out / ".git").exists():
        die(f"no output worktree at {out}; create it from your clone with:  "
            f"git worktree add {out} {s['output_branch']}")
    branch = git(out, "rev-parse", "--abbrev-ref", "HEAD", capture=True)
    if branch != s["output_branch"]:
        die(f"{out} is on branch {branch}, not {s['output_branch']}")

    git(out, "pull", "-q", "--ff-only", "origin", s["output_branch"])
    target = out / s["published_dir"] / page.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(page, target)
    rel = f"{s['published_dir']}/{page.name}"
    git(out, "add", rel)
    staged = subprocess.run(["git", "-C", str(out), "diff", "--cached", "--quiet"]).returncode
    if staged:
        git(out, "commit", "-q", "-m", f"narrated: {page.name} ({date.today().isoformat()})")
        git(out, "push", "-q", "origin", s["output_branch"])
        print(f"output : {rel} pushed ({git(out, 'log', '--oneline', '-1', capture=True)})")
    else:
        print(f"output : {rel} is unchanged on {s['output_branch']}; nothing to commit")

    url = pages_url(s["repo"], s["published_dir"], page.name)
    if s["hash_list"]:
        digest = hashlib.sha256(page.read_bytes()).hexdigest()
        line, changed, replaced = update_hash_list(s["hash_list"], digest, page.name)
        rel_list = os.path.relpath(s["hash_list"], s["root"])
        if changed:
            print(f"hash   : {'replaced' if replaced else 'added'} in {s['hash_list']}:\n         {line}")
            print("\nThe page is served only after this change is merged on main. In "
                  f"{s['root']}:\n"
                  f"  git switch -c narrated/{page.stem} origin/main\n"
                  f"  git add {rel_list}\n"
                  f"  git commit -m \"{rel_list}: {page.name}\"\n"
                  f"  git push -u origin narrated/{page.stem}\n"
                  f"then open and merge the pull request; the merge starts the Pages workflow.\n"
                  f"Until then the Pages build fails at the hash check, so merge it soon.")
        else:
            print(f"hash   : already listed in {rel_list}; nothing to change on main")
            if staged:
                print("         (the page on output changed but its hash did not: identical content)")
    elif args.no_dispatch:
        print("Pages  : not started (--no-dispatch)")
    elif shutil.which("gh") and subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0:
        subprocess.run(["gh", "workflow", "run", s["pages_workflow"], "--ref", "main", "-R", s["repo"]], check=False)
        print("Pages  : workflow started; it takes a minute or two.")
    else:
        print(f"Pages  : start it at https://github.com/{s['repo']}/actions/workflows/{s['pages_workflow']}"
              " -> Run workflow")
    print(f"\nPlay online : {url}")
    print(f"Single file : https://github.com/{s['repo']}/blob/{s['output_branch']}/{rel} (Download raw file)")


def cmd_build_deck(args):
    from . import deck
    talk = Path(args.talk).expanduser()
    s = load_settings()
    name = args.name or talk.resolve().name
    out = Path(args.out).expanduser() if args.out else talk / f"{name}.html"
    macros_file = Path(args.macros).expanduser() if args.macros else s["deck_macros"]
    macros = {}
    if macros_file:
        if not macros_file.is_file():
            die(f"macros file not found: {macros_file}")
        macros = json.loads(macros_file.read_text(encoding="utf-8"))
    assets = Path(args.assets).expanduser() if args.assets else s["deck_assets"]
    starts = [p for p in (s["root"], Path.cwd()) if p]
    try:
        r = deck.build(talk, out, assets=assets, foot=args.foot, macros=macros, node_starts=starts)
    except deck.DeckError as e:
        die(str(e))
    print(f"{r['out']}: {r['slides']} slides, {r['with_notes']} with notes, {r['words']} words "
          f"(about {r['words'] / 140:.0f} min at 140 words a minute), {r['mb']:.1f} MB; "
          f"{'its own frame' if r['own_frame'] else 'narrate frame'}")
    if r["missing"]:
        print(f"no notes file for slide(s) {', '.join(map(str, r['missing']))}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="narrate", description="Render and publish narrated slide pages.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config", help="show the settings found for this directory")
    r = sub.add_parser("render", help="narrate a slides page (other options go to voiceover)")
    r.add_argument("slides")
    r.add_argument("-d", "--outdir", help="output folder (default: <narration_dir>/<--name or deck name>)")
    r.add_argument("--pronunciations", help="an extra pronunciation file, applied last")
    r.add_argument("--dry-run", action="store_true", help="show the voiceover command and stop")
    p = sub.add_parser("publish", help="push a checked page to the output branch")
    p.add_argument("page")
    p.add_argument("--no-dispatch", action="store_true", help="do not start the Pages workflow")
    b = sub.add_parser("build-deck", help="build a slides page from slides.html and notes/")
    b.add_argument("talk", help="talk folder (slides.html, notes/slide_NN.md)")
    b.add_argument("--name", help="page name (default: the folder name); writes <talk>/<name>.html")
    b.add_argument("--out", help="write the page here instead")
    b.add_argument("--foot", default="", help="footer text before the slide number")
    b.add_argument("--assets", help="folder of the images named asset:F (default: [deck] assets)")
    b.add_argument("--macros", help="JSON file of TeX macros (default: [deck] macros)")
    args, rest = ap.parse_known_args(argv)
    if args.cmd == "render":
        cmd_render(args, rest)
    elif rest:
        ap.error(f"unrecognized arguments: {' '.join(rest)}")
    elif args.cmd == "config":
        cmd_config(args)
    elif args.cmd == "build-deck":
        cmd_build_deck(args)
    else:
        cmd_publish(args)


if __name__ == "__main__":
    main()
