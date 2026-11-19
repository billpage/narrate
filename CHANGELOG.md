# Changelog

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
