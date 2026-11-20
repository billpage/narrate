# Changelog

## 1.0.0 (20 November 2026)

No change to the code or its output: the version number only. It marks step 7
of the plan, the last: billpage/wpmw uses the package and has deleted its
`voiceover.py`, `narrate.sh` and `publish_narrated.sh` (wpmw branch
`claude/switch-to-narrate`). Its deck `worlds_and_particles` is now built with
`narrate build-deck` from `talks/worlds_and_particles/`, so it has narrate's
frame; its spoken text is unchanged.

To switch from 0.5.0: change the tag to `v1.0.0`. Nothing else.

To switch from wpmw's own tools (as wpmw did): add `narration.toml`
(`[voice]` replaces `WPMW_VOICE`, `WPMW_PAUSE` and `narrate.sh`'s defaults);
call `narrate render` and `narrate publish` where `narrate.sh` and
`publish_narrated.sh` were called; compare `narrate render … --preview` with
the old `--preview` before a long render.

## 0.5.0 (19 November 2026)

- `narrate test-pronunciation WORDS.json [--slides PAGE]`: one self-contained
  page of players to choose spellings by ear. Per word: the word as written,
  read by a reference voice of its own language (`_reference_voice`, or per
  word; Edge); each spelling (the candidates, the one now in use, and the word
  as written) read by the talk's voice alone and inside sentences from the
  notes, the rest of each sentence spoken as in the talk. A spelling is sent as
  it is, never through the pronunciations, so "as written" is heard as written.
  One choice per word; "Copy JSON" gives `{written: spoken}`. Clips are cached
  by voice, rate and text.
- tests: 13 (new: the page end to end with the silent voice and the cache; the
  exact texts sent to the voice; a bad words file).

`voiceover`, `render`, `publish` and `build-deck` unchanged. Nothing to switch.

## 0.4.0 (19 November 2026)

- `narrate build-deck TALK`: a slides page from `slides.html` and
  `notes/slide_NN.md`, with TeX typeset as SVG by MathJax, `asset:` images
  embedded and footers added. From billpage/oziewicz `src/narration/build_deck.py`
  and `tex_svg.mjs`, with these changes: TeX macros come from the project
  (`[deck] macros`), MathJax from the project's `node_modules`; slides are
  found by class token (`class="slide title"` counts, and a `<div>` slide
  with nested `<div>`s gets its footer at its own end); the page is written to
  `<talk>/<name>.html` or `--out`.
- The shared slide-page frame (`frame/frame.css`, `frame/frame.html`): stage
  geometry, notes panel at the right (below in a narrow window, N toggles),
  bar, navigation script and print rules, from the oziewicz Grassmann–Clifford
  deck. A source without a frame gets it; a source with its own keeps it.
- `INTERFACE.md`: the deck source.
- tests: 10 (new: build-deck with frame, TeX, asset, footers and nested
  slides; a source with its own frame; refusals).

Checked on oziewicz `talks/grassmann_to_clifford` (773505c): built from its
`slides.html` as it is (own frame), the page is byte-identical to the committed
one; built from the same source with its frame removed (narrate's frame
added), all 23 slides are pixel-identical in Chrome with notes shown, hidden
and below (narrow window), and so is the print layout. `voiceover` unchanged.

To switch (oziewicz): `narrate build-deck` in place of `build_deck.py`; TeX
macros to a JSON file named in `[deck] macros`.

## 0.3.1 (19 November 2026)

- `narrate render … --name NAME` renders into `<narration_dir>/NAME/`, not
  `<narration_dir>/<deck name>/`, so two renders of one page under different
  names no longer share a folder (and its `slide_NN.mp3` copies).
- The `run :` line shows the slides page again.
- `README.md`: install with `pipx` (a plain `pip install` is refused by the
  system Python of Debian, Ubuntu and Mint).

To switch: `pipx install --force "narrate[pptx] @
git+https://github.com/billpage/narrate@v0.3.1"`. A render that used `--name`
without `-d` now goes to a new folder; move the old folder there to keep its
clips.

## 0.3.0 (19 November 2026)

- `narrate render` and `narrate publish`, with settings from `narration.toml`
  (see `narrate --help`), in place of wpmw's `narrate.sh` and
  `publish_narrated.sh`.
- Pronunciations in three layers: `narrate/terms/common.json` (the 13 physics
  entries that were the `pptx-voiceover` skill's example), the project's
  `terms`, the talk's `pronunciations.json`; merged into
  `<outdir>/<name>_terms.json`.
- Hash gate: with `hash_list` set, `publish` writes the page's SHA-256 line in
  the working copy and does not start the Pages workflow.
- `publish` refuses a page whose audio is linked (`--link`). wpmw's
  `publish_narrated.sh` looked for `const EMBEDDED = false`, which the page
  never contains (it writes `const SW = .., SH = .., EMBEDDED = false`), so its
  check never fired.
- `tests/`: a three-slide demo project and pytest tests.

`voiceover` is unchanged. To switch a project: add `narration.toml`; call
`narrate render` and `narrate publish` where `narrate.sh` and
`publish_narrated.sh` were called. The package layer can change spoken text
(for example `ψ₀` becomes "psi zero" instead of "psi 0"), so run
`narrate render … --preview` and compare `<name>_spoken.txt` before a long
render; `package_terms = false` turns the layer off.

## 0.2.1 (19 November 2026)

- A slides page without `</head>` now stops with an error message instead
  of a Python `ValueError` traceback.
- `README.md` installs the current tag (it still named `v0.1.0`).

To switch: change the tag to `v0.2.1`. Output is unchanged.

## 0.2.0 (19 November 2026)

- Clips are kept in `audio/clips/` under a hash of their spoken text and
  settings, so inserting, removing or moving a slide no longer remakes every
  later slide. Clips of an earlier render are adopted, so nothing finished is
  synthesised again. `--max-chars` and `--join` are now part of what decides
  whether a clip is remade.
- Slides are counted as the player counts them: elements whose class list
  contains `slide`. `class="slide title"` is now accepted; before, it gave
  "N slides but M notes".
- `INTERFACE.md`: what a slides page must contain.

To switch: change the tag to `v0.2.0`. Nothing else; output is unchanged.

## 0.1.0 (19 November 2026)

`voiceover.py` from billpage/wpmw at `0f1d154`, unchanged, installed as the
`voiceover` command. To switch: `pip install "narrate[pptx] @
git+https://github.com/billpage/narrate@v0.1.0"` and call `voiceover` where
`python3 voiceover.py` was called.
