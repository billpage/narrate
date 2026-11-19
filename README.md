# narrate

Narrate a slide deck from its speaker notes with text-to-speech: a
self-contained web page (slides, audio player, transcript) by default,
optionally a PowerPoint with click-to-play audio.

```bash
pip install "narrate[pptx] @ git+https://github.com/billpage/narrate@v0.2.1"
voiceover --help
```

`ffmpeg` is needed for `--reencode`, `--declick`, `--highpass` and the
`silent` and `piper` back-ends; `flite` for the `flite` back-end.

## Status

Version 0.1.0 is `src/narration/voiceover.py` from
[billpage/wpmw](https://github.com/billpage/wpmw) at commit `0f1d154`
(11 November 2026), moved here unchanged, with a `voiceover` command in place
of `python3 voiceover.py`. The plan for the rest of the package (a `narrate`
command with per-project settings, a deck builder for TeX sources, shared
pronunciations) is in [`PLAN.md`](PLAN.md).

## License

[MIT](LICENSE). The code came from wpmw, where it was AGPL-3.0-or-later; its
author relicensed it here, so that narrated pages, which carry a copy of the
player script, can be used by anyone under any terms.
