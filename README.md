# narrate

Narrate a slide deck from its speaker notes with text-to-speech: a
self-contained web page (slides, audio player, transcript) by default,
optionally a PowerPoint with click-to-play audio.

```bash
pipx install "narrate[pptx] @ git+https://github.com/billpage/narrate@v0.3.1"
voiceover --help      # the narrator itself
narrate --help        # the narrator with a project's settings, and publishing
```

`pipx` (`sudo apt install pipx`) gives the two commands their own environment;
a plain `pip install` is refused by the system Python of Debian, Ubuntu and
Mint (PEP 668). To move to a later tag, run the same line with `--force` and
the new tag. Inside a virtual environment, `pip install` with the same argument
works too.

## In a project

A repository that narrates talks keeps its settings in `narration.toml` at its
root. For billpage/oziewicz it would be (planned; the terms file does not exist yet):

```toml
repo = "billpage/oziewicz"
narration_dir = "~/oziewicz-narration"     # renders go to <narration_dir>/<deck name>/
output_worktree = "~/oziewicz-output"      # a worktree of the output branch
terms = ["src/narration/oziewicz_terms.json"]
hash_list = "talks/narrated.sha256"        # publish gate; leave out for none

[voice]
voice = "en-CA-LiamNeural"
pause = 30
reencode = 32
```

Then, anywhere inside the repository:

```bash
narrate render talks/grassmann_to_clifford/grassmann_to_clifford.html --preview
narrate render talks/grassmann_to_clifford/grassmann_to_clifford.html
narrate publish ~/oziewicz-narration/grassmann_to_clifford/grassmann_to_clifford_narrated.html
```

Options after the slides page go to `voiceover` (`--resynth 5`, `--tts piper`,
…) and override `[voice]`; `--name` also names the folder, so two renders of
one page (two voices, say) do not share one. Pronunciations are merged from three layers, a later
one winning on the same key: narrate's `terms/common.json`, the project's
`terms`, and the talk's `pronunciations.json` beside the slides page. With a
hash gate, `publish` pushes the page to the output branch and writes its
SHA-256 into the hash list in your working copy, for a pull request to `main`;
without one it starts the Pages workflow. All settings: `narrate --help`.

Tests: `pip install -e . pytest && pytest -q tests` (needs `ffmpeg` and `git`;
publishing goes to a temporary local repository).

`ffmpeg` is needed for `--reencode`, `--declick`, `--highpass` and the
`silent` and `piper` back-ends; `flite` for the `flite` back-end.

## Status

Version 0.1.0 is `src/narration/voiceover.py` from
[billpage/wpmw](https://github.com/billpage/wpmw) at commit `0f1d154`
(11 November 2026), moved here unchanged, with a `voiceover` command in place
of `python3 voiceover.py`. Version 0.3.0 adds the `narrate` command in place of
wpmw's `narrate.sh` and `publish_narrated.sh`. The rest of the plan (a deck
builder for TeX sources, a pronunciation test page) is in [`PLAN.md`](PLAN.md).

## License

[MIT](LICENSE). The code came from wpmw, where it was AGPL-3.0-or-later; its
author relicensed it here, so that narrated pages, which carry a copy of the
player script, can be used by anyone under any terms.
