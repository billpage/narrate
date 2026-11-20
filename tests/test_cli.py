"""Tests of the `narrate` command on the demo project in tests/demo.

Run:  pip install -e . pytest && pytest -q tests
Needs ffmpeg (the demo uses the silent voice) and git. Publishing goes to a
bare repository in a temporary folder that stands in for GitHub.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).with_name("demo")
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def narrate(cwd, *args, check=True):
    r = subprocess.run([sys.executable, "-m", "narrate.cli", *args], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and r.returncode:
        raise AssertionError(f"narrate {' '.join(args)} exited {r.returncode}:\n{r.stdout}")
    return r


def top_level(toml, line):
    """Add a top-level setting to narration.toml (before its first table)."""
    text = toml.read_text()
    i = text.index("\n[") + 1
    toml.write_text(text[:i] + line + "\n" + text[i:])


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@invalid", *args],
                          cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


@pytest.fixture
def project(tmp_path):
    """The demo project, with a bare 'origin' holding main and output, and an output worktree."""
    root = tmp_path / "demo"
    shutil.copytree(DEMO, root, ignore=shutil.ignore_patterns("build"))
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "demo")
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-q", "origin", "main")
    git(root, "switch", "-q", "--orphan", "output")
    git(root, "commit", "-q", "--allow-empty", "-m", "output branch")
    git(root, "push", "-q", "origin", "output")
    git(root, "switch", "-q", "main")
    out = tmp_path / "demo-output"
    git(tmp_path, "clone", "-q", "-b", "output", str(origin), str(out))
    toml = root / "narration.toml"
    toml.write_text(toml.read_text()
                    .replace('narration_dir = "build/narration"', f'narration_dir = "{tmp_path / "narration"}"')
                    .replace('output_worktree = "build/demo-output"', f'output_worktree = "{out}"'))
    return {"root": root, "origin": origin, "out": out, "renders": tmp_path / "narration"}


def spoken(project):
    text = (project["renders"] / "demo" / "demo_spoken.txt").read_text(encoding="utf-8")
    return [block.split("---\n", 1)[1].strip() for block in text.split("--- slide ")[1:]]


def test_layers_merge_in_order(project):
    narrate(project["root"], "render", "talks/demo/demo.html", "--preview")
    assert spoken(project) == [
        "oh-zheh-veech wrote h-bar for the reduced constant.",       # project term, package term
        "We red the papers. psi nought is the initial state.",       # talk beats package (ψ₀)
        "capital gamma is the gamma function; the conclusion.",      # talk beats project (the end)
    ]
    merged = json.loads((project["renders"] / "demo" / "demo_terms.json").read_text(encoding="utf-8"))
    assert merged["the end"] == "the conclusion" and merged["ψ₀"] == "psi nought" and merged["ℏ"] == "h-bar"


def test_command_line_layer_wins_and_package_terms_can_be_off(project, tmp_path):
    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps({"the end": "the very end"}), encoding="utf-8")
    toml = project["root"] / "narration.toml"
    top_level(toml, "package_terms = false")
    narrate(project["root"], "render", "talks/demo/demo.html", "--preview", "--pronunciations", str(extra))
    lines = spoken(project)
    assert "h-bar" not in lines[0]                  # ℏ comes from the package layer, now off
    assert lines[2].endswith("the very end.")


def test_voice_settings_and_override(project):
    r = narrate(project["root"], "render", "talks/demo/demo.html", "--dry-run")
    assert "--tts silent" in r.stdout and "--reencode 32" in r.stdout
    toml = project["root"] / "narration.toml"
    toml.write_text(toml.read_text().replace('tts = "silent"', 'tts = "edge"\nvoice = "en-CA-LiamNeural"\npause = 30'))
    r = narrate(project["root"], "render", "talks/demo/demo.html", "--dry-run")
    assert "--voice en-CA-LiamNeural" in r.stdout and "--pause 30" in r.stdout
    r = narrate(project["root"], "render", "talks/demo/demo.html", "--dry-run", "--tts", "flite")
    assert "LiamNeural" not in r.stdout and "--pause" not in r.stdout and "--reencode 32" in r.stdout


def test_unknown_setting_is_refused(project):
    toml = project["root"] / "narration.toml"
    top_level(toml, 'hashlist = "x"')
    toml.write_text(toml.read_text() + 'speed = 2\n')
    r = narrate(project["root"], "config", check=False)
    assert r.returncode == 1 and "unknown setting(s): hashlist, voice.speed" in r.stdout


@needs_ffmpeg
def test_render_and_publish_with_hash_gate(project):
    narrate(project["root"], "render", "talks/demo/demo.html")
    page = project["renders"] / "demo" / "demo_narrated.html"
    assert page.is_file()
    digest = hashlib.sha256(page.read_bytes()).hexdigest()

    r = narrate(project["root"], "publish", str(page))
    assert "pushed" in r.stdout and "Pages  :" not in r.stdout       # the gate: no workflow started
    listed = (project["root"] / "talks" / "narrated.sha256").read_text().splitlines()
    assert listed == [f"{digest}  demo_narrated.html"]
    on_origin = subprocess.run(["git", "--git-dir", str(project["origin"]), "show",
                                "output:narrated/demo_narrated.html"], check=True, capture_output=True).stdout
    assert hashlib.sha256(on_origin).hexdigest() == digest            # pushed byte for byte
    assert "https://example.github.io/demo/narrated/demo_narrated.html" in r.stdout

    r = narrate(project["root"], "publish", str(page))               # again: nothing to do
    assert "unchanged" in r.stdout and "already listed" in r.stdout

    # a new version of the page replaces the old line instead of adding one
    talk = project["root"] / "talks" / "demo" / "pronunciations.json"
    talk.write_text(talk.read_text().replace('"the conclusion"', '"the very last part"'), encoding="utf-8")
    narrate(project["root"], "render", "talks/demo/demo.html")
    r = narrate(project["root"], "publish", str(page))
    new = hashlib.sha256(page.read_bytes()).hexdigest()
    assert new != digest and "replaced" in r.stdout
    assert (project["root"] / "talks" / "narrated.sha256").read_text().splitlines() == [f"{new}  demo_narrated.html"]


@needs_ffmpeg
def test_publish_without_gate_and_refusals(project):
    toml = project["root"] / "narration.toml"
    toml.write_text(toml.read_text().replace('hash_list = "talks/narrated.sha256"\n', ""))
    narrate(project["root"], "render", "talks/demo/demo.html")
    page = project["renders"] / "demo" / "demo_narrated.html"
    r = narrate(project["root"], "publish", str(page), "--no-dispatch")
    assert "pushed" in r.stdout and "not started (--no-dispatch)" in r.stdout
    assert not (project["root"] / "talks" / "narrated.sha256").exists()

    linked_dir = project["renders"] / "linked"
    narrate(project["root"], "render", "talks/demo/demo.html", "--link", "-d", str(linked_dir))
    r = narrate(project["root"], "publish", str(linked_dir / "demo_narrated.html"), check=False)
    assert r.returncode == 1 and "links its audio" in r.stdout
    r = narrate(project["root"], "publish", str(project["root"] / "talks" / "demo" / "demo.html"), check=False)
    assert r.returncode == 1 and "_narrated.html" in r.stdout


def test_name_sets_folder_and_run_line_shows_page(project):
    r = narrate(project["root"], "render", "talks/demo/demo.html", "--name", "demo_b", "--preview")
    assert "run    : voiceover talks/demo/demo.html -d " in r.stdout
    folder = project["renders"] / "demo_b"
    assert (folder / "demo_b_spoken.txt").is_file() and (folder / "demo_b_terms.json").is_file()
    assert not (project["renders"] / "demo").exists()


def mathjax_available():
    root = Path(__file__).resolve().parents[1]
    return shutil.which("node") and any((d / "node_modules" / "mathjax-full").is_dir()
                                        for d in [root, *root.parents])


@pytest.mark.skipif(not mathjax_available(), reason="node or mathjax-full not installed")
def test_build_deck_with_frame_math_assets_footers(project):
    repo = Path(__file__).resolve().parents[1]
    nm = next(d / "node_modules" for d in [repo, *repo.parents] if (d / "node_modules" / "mathjax-full").is_dir())
    (project["root"] / "node_modules").symlink_to(nm)    # a project has its own `npm install mathjax-full`
    r = narrate(project["root"], "build-deck", "talks/texdemo", "--foot", "Demo")
    page = (project["root"] / "talks" / "texdemo" / "texdemo.html").read_text(encoding="utf-8")
    assert "3 slides, 2 with notes" in r.stdout and "narrate frame" in r.stdout
    assert "no notes file for slide(s) 3" in r.stdout
    assert "Demo · 1 / 3" not in page                     # data-nofoot
    assert "Demo · 2 / 3" in page and "Demo · 3 / 3" in page
    assert page.index("Demo · 3 / 3") > page.index('class="fig"')   # footer at the end of slide 3, not inside the figure
    assert "\\(" not in page and "\\[" not in page and page.count("<svg") >= 2
    assert 'fill="#2f5d8a"' in page                   # the project's macro \V (RGB 47,93,138) was used
    assert "data:image/svg+xml;base64," in page          # asset embedded
    frame, own = page.index("narrate frame: stage and slide geometry"), page.index(".slide { background: #fff")
    assert frame < own                                   # frame style first, the deck's own style can override
    assert 'const NOTES = ["This is the title slide.", "E equals m c squared.", ""];' in page
    r = narrate(project["root"], "render", "talks/texdemo/texdemo.html", "--preview")
    assert "(3 slides, 2 with notes)" in r.stdout        # voiceover reads the built page


def test_build_deck_keeps_a_source_frame(project):
    talk = project["root"] / "talks" / "own"
    (talk / "notes").mkdir(parents=True)
    (talk / "slides.html").write_text(
        '<html><head><style>.slide{}</style></head><body>\n<div id="stage">\n'
        '<section class="slide">one</section>\n<section class="slide">two</section>\n</div>\n'
        '<div id="notes"></div>\n<script>\nconst NOTES = [];\n</script>\n</body></html>\n', encoding="utf-8")
    (talk / "notes" / "slide_02.md").write_text("Second.\n", encoding="utf-8")
    r = narrate(project["root"], "build-deck", "talks/own", "--name", "own_page")
    page = (talk / "own_page.html").read_text(encoding="utf-8")
    assert "its own frame" in r.stdout and "narrate frame" not in page
    assert 'const NOTES = ["", "Second."];' in page and "· 2 / 2</p>" in page


def test_build_deck_refusals(project):
    talk = project["root"] / "talks" / "bad"
    talk.mkdir(parents=True)
    (talk / "slides.html").write_text('<html><head></head><body><div id="stage"><p>x</p></div></body></html>')
    r = narrate(project["root"], "build-deck", "talks/bad", check=False)
    assert r.returncode == 1 and "no element with the class `slide`" in r.stdout
    (talk / "slides.html").write_text('<html><head></head><body><div id="stage"><section class="slide">'
                                      '<img src="asset:none.png"></section></div></body></html>')
    r = narrate(project["root"], "build-deck", "talks/bad", check=False)
    assert r.returncode == 1 and "asset not found" in r.stdout
