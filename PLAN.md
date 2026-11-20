# Plan

Where the narration tools come from, what this package will contain, and the
order of work. From the proposal of 19 November 2026 (Oziewicz Project,
`claude/narration_package_proposal.md`), with answers to its open questions.
Decisions were confirmed by the owner on 19 November 2026.

## Where the code comes from

| Now | Becomes |
|---|---|
| wpmw `src/narration/voiceover.py` | `narrate.voiceover` (v0.1.0, unchanged) |
| wpmw `src/narration/narrate.sh`, `publish_narrated.sh` | `narrate render`, `narrate publish` |
| oziewicz `src/narration/build_deck.py`, `tex_svg.mjs` | `narrate build-deck` |
| oziewicz `src/narration/build_slides.py` | stays in oziewicz (NPA 2009 only) |
| claude-plugins `pptx-voiceover`: `curl` of wpmw `main` | `pip install` of a tag |

The `pptx-voiceover` skill has no copy of `voiceover.py`. It downloads the
current file from wpmw's `main` branch, so every change there reaches the skill
unpinned, and moving the file would break the skill. Switching the skill to a
tag is the first change after v0.1.0.

**Freeze rule.** From wpmw commit `0f1d154` on, `voiceover.py` changes here
only. wpmw's copy is not edited until wpmw switches to the package and deletes
it.

## Check of v0.1.0

The packaged `voiceover` and wpmw's `voiceover.py` at `0f1d154` were run on
oziewicz `talks/grassmann_to_clifford/grassmann_to_clifford.html` (oziewicz
commit `28f0e38`) with `--tts silent --pronunciations pronunciations.json
--reencode 32`. The spoken text (263 lines), the 23 clips and the narrated page
(SHA-256 `3d64f15a…`) are byte-identical. Edge was not tested (not reachable
from the sandbox); the code path is the same file.

## Decisions

1. **Name.** `billpage/narrate`, Python package `narrate`, installed from a git
   tag (not PyPI).
2. **Licence: MIT** (decided 19 November 2026). `voiceover` copies its player
   script into every narrated page, so under AGPL each page would carry AGPL
   code, a deterrent for anyone narrating their own talk.
3. **Pronunciations: three layers, merged** (decided). Package
   `terms/*.json` (names and terms common to several projects: Oziewicz,
   Jadczyk, Weyl, spinor, …) < project file(s) named in `narration.toml` < the
   talk's `pronunciations.json`. A later layer wins on the same key; the merged
   table is then applied longest key first, as today. On 19 November 2026 the
   four existing files (wpmw 147 entries, skill 13, Grassmann–Clifford 45, NPA
   2009 23) share no key, so merging changes nothing. The skill's
   `pronunciations-physics.json` moves into the package layer.
4. **Player template** stays in `voiceover`: it is the format of its output.
   The slide-page *frame* (navigation script, CSS, notes panel) is the format of
   its input and goes with `build-deck`.
5. **Cache keyed by spoken text: now** (decided). The key already exists
   (`tts|voice|rate` + text, kept in `slide_NN.txt`); only the file name uses
   the slide number. Store clips as `audio/clips/<hash>.mp3`, hash of the key
   plus `max_chars` and `join` (both change the clip), and adopt existing
   `slide_NN.mp3` whose stamp matches, so no finished render is synthesised
   again. Done in v0.2.0; see `INTERFACE.md`.
6. **Slide count.** `deck_from_html` counts the substring `class="slide"`, so
   `class="slide title"` is missed. Count `<section>` elements whose class list
   contains the token `slide`, as the player does. Done in v0.2.0.

## Order of work

| Step | Change | Tag |
|---|---|---|
| 0 | `voiceover` moved unchanged; `pip install` works: done | v0.1.0 |
| 1 | `pptx-voiceover` installs a tag instead of `curl` from wpmw: done | (claude-plugins) |
| 2 | cache by spoken text; slide count by class token; written interface (`INTERFACE.md`): done | v0.2.0, v0.2.1 |
| 3 | `narrate render` / `narrate publish` with `narration.toml` and the hash gate; package terms layer: done | v0.3.0, v0.3.1 |
| 4 | oziewicz switches (the case with the hash gate first): done | (oziewicz) |
| 5 | `narrate build-deck` and the frame; oziewicz drops `build_deck.py`, `tex_svg.mjs`: done | v0.4.0 |
| 6 | `narrate test-pronunciation` (candidate spellings, alone and in sentences, chosen and reference voice, one page of players): done | v0.5.0 |
| 7 | wpmw switches and deletes its copy | v1.0.0 |

wpmw keeps working, untouched, until step 7.

## Step 7 brief: switching wpmw (for the session that does it)

Written 20 November 2026 at the end of the session that built v0.1.0 to
v0.5.0 in the Oziewicz Project. The next session runs in the WPMW Project and
cannot see that conversation; this section, `CHANGELOG.md`, `INTERFACE.md` and
`AGENTS.md` are the record.

**State.** narrate `v0.5.0` is tagged (`main` at `740959d`). oziewicz uses it
(`narration.toml` with the hash gate, `src/narration/oziewicz_terms.json`,
the Grassmann–Clifford deck built with `build-deck`). The `pptx-voiceover`
skill pins `v0.5.0` (plugin 0.3.5). wpmw is untouched at `0f1d154`; its
`voiceover.py` is frozen there (the freeze rule above).

**What wpmw has** (all at `0f1d154`):

- `src/narration/`: `voiceover.py`, `narrate.sh` (voice `en-CA-LiamNeural`,
  pause 30, re-encode 32, terms `wpmw_terms.json`; environment variables
  `WPMW_VOICE`, `WPMW_PAUSE`; renders in `~/wpmw-narration/<name>/`),
  `publish_narrated.sh` (output worktree `~/wpmw-output`, starts the `pages`
  workflow with `gh`; no hash gate), `wpmw_terms.json` (148 entries),
  `README.md`.
- One narrated deck: `docs/interactive/worlds_and_particles.html`, with its own
  frame (the older one: notes in a strip below the slide) and `NOTES` written
  in the page, not in `notes/` files. `chord_reading.html` and `sea_lock.html`
  are interactive pages, not decks. Published page:
  `https://billpage.github.io/wpmw/narrated/worlds_and_particles_narrated.html`.
- Text that names the old tools: `README.md` (lines 246–267),
  `src/README.md` (1531–1537), `.github/workflows/pages.yml` (comments,
  lines 6–16), `src/narration/README.md`.

**Tasks.**

1. `narration.toml` at the wpmw root: `repo = "billpage/wpmw"`,
   `narration_dir = "~/wpmw-narration"`, `output_worktree = "~/wpmw-output"`,
   `terms = ["src/narration/wpmw_terms.json"]`, no `hash_list`; `[voice]`
   `voice = "en-CA-LiamNeural"`, `pause = 30`, `reencode = 32`. The two
   environment variables go (the command line overrides `[voice]`).
2. Compare spoken text before anything else: wpmw's `voiceover.py` with
   `--pronunciations src/narration/wpmw_terms.json --preview` against
   `narrate render docs/interactive/worlds_and_particles.html --preview`,
   slide by slide. Differences can come only from narrate's package layer
   (`terms/common.json`, e.g. `ψ₀` → "psi zero"); list them for the owner, who
   may keep them or set `package_terms = false`. Where the text is unchanged,
   the clips in `~/wpmw-narration/worlds_and_particles/audio/` are adopted and
   nothing is synthesised again.
3. Ask the owner about the deck's frame: keep its own (nothing to do; a page
   with its own frame stays as it is), or move it to `slides.html` +
   `notes/slide_NN.md` and `narrate build-deck` with narrate's frame (notes at
   the right). The second is a larger change; if chosen, check it as the
   Grassmann–Clifford deck was checked: stage and `NOTES` byte-identical, and
   every slide compared by screenshot in Chrome with Playwright
   (`/usr/bin/google-chrome`), in a wide window with notes shown and hidden, a
   narrow window, and print layout, with a control pair of different slides.
   Here the frame changes on purpose, so compare the slides themselves (the
   stage), not the whole window.
4. Delete `voiceover.py`, `narrate.sh`, `publish_narrated.sh`; keep
   `wpmw_terms.json`. Rewrite `src/narration/README.md` for `narrate`
   (install with `pipx`; `narrate render`, `narrate publish`) and update the
   other text listed above. wpmw's own rules (`AGENTS.md`, its checks) apply.
5. Then narrate `v1.0.0` (step 7's tag): remove the freeze rule and this brief
   from `PLAN.md`, move `README.md` and the skill pin to `v1.0.0`, and the
   oziewicz talk READMEs (still at `v0.4.0`) at the same time.

**Practical notes.** The owner installs with `pipx` (Mint refuses a plain
`pip install`) and renders on his machine: Edge is not reachable from
Claude's sandbox, so check there with `--tts silent`. He merges with "Create
a merge commit" and makes the tags. wpmw's `publish_narrated.sh` looked for
`const EMBEDDED = false`, which no page contains, so it never refused a page
with linked audio; `narrate publish` does.

## Lessons to carry (from the Grassmann–Clifford session)

- Spelling is the only lever on Edge pronunciation: Edge ignores SSML phoneme
  tags. Capitals may be spelled as letters; a leading "Ar-" was read as A, R.
  Homographs need phrase keys (`Why read` → `Why reed`).
- Greek capitals are already spoken as "capital …": write "Γ", not
  "capital Γ".
- Hash gate: Pages stops serving a replaced page until its new hash is merged,
  so `narrate publish` should prepare the hash line and name the file on `main`.
- New server: `git`, `python3-venv`, `ffmpeg`, `tmux`; an SSH key for pushing;
  one `edge-tts` call before a 30-minute render.
