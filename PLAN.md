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
| 1 | `pptx-voiceover` installs v0.1.0 instead of `curl` from wpmw | (claude-plugins) |
| 2 | cache by spoken text; slide count by class token; written interface (`INTERFACE.md`): done | v0.2.0 |
| 3 | `narrate render` / `narrate publish` with `narration.toml` and the hash gate; package terms layer | v0.3.0 |
| 4 | oziewicz switches (the case with the hash gate first) | (oziewicz) |
| 5 | `narrate build-deck` and the frame; oziewicz drops `build_deck.py`, `tex_svg.mjs` | v0.4.0 |
| 6 | `narrate test-pronunciation` (candidate spellings, alone and in sentences, chosen and reference voice, one page of players) | v0.5.0 |
| 7 | wpmw switches and deletes its copy | v1.0.0 |

wpmw keeps working, untouched, until step 7.

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
