"""Compare candidate spellings by ear (`narrate test-pronunciation`).

The words file is a JSON object, one entry per written word:

    {
      "_reference_voice": "pl-PL-MarekNeural",
      "Oziewicz": ["oh-zheh-veech", "oh-zhe-vich"],
      "Chevalley": {"candidates": ["Shuh-vah-lay", "Sheh-vah-lee"],
                    "reference_voice": "fr-FR-HenriNeural"}
    }

Keys starting with `_` are settings (`_reference_voice`, `_sentences`). For each
word the page has players for:

- the word as written, read by the reference voice (a voice of the word's own
  language, which reads the original spelling, accents included; Edge only);
- each spelling read by the talk's voice: the candidates, the spelling now in
  the merged pronunciations ("current"), and the word as written (what the
  voice says with no entry). A spelling is sent as it is (only accents and
  symbols are cleaned), never through the pronunciations;
- each spelling inside sentences from the notes of a slides page (--slides),
  shortest first, with the rest of the sentence spoken as in the talk.

One spelling per word can be chosen on the page; "Copy JSON" copies the choices
as {written: spoken} for the project's or the talk's terms file. Clips are kept
in <dir>/clips under a hash of voice, rate and text, so a second run with one
more candidate synthesises only that one.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

from . import voiceover

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
MAX_WORDS = 36           # longer sentences are cut to a window around the word
WINDOW = 14              # words on each side of the word in a cut sentence


SLOT = "\ue000"           # holds the spelling's place while the rest of a sentence is cleaned


class PronounceError(Exception):
    pass


def read_words(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PronounceError(f"{path}: expected a JSON object")
    settings = {k[1:]: v for k, v in data.items() if k.startswith("_")}
    words = []
    for word, v in data.items():
        if word.startswith("_"):
            continue
        if isinstance(v, list):
            v = {"candidates": v}
        if not isinstance(v, dict) or not isinstance(v.get("candidates", []), list):
            raise PronounceError(f"{path}: {word!r} needs a list of candidate spellings")
        words.append({"word": word, "candidates": [str(c) for c in v.get("candidates", [])],
                      "reference_voice": v.get("reference_voice")})
    if not words:
        raise PronounceError(f"{path}: no words")
    return settings, words


def word_pattern(word):
    return re.compile(rf"(?<![\w]){re.escape(word)}(?![\w])")


def sentences_with(word, notes, n):
    """Up to n distinct sentences of the notes containing the word, shortest first."""
    pat, found = word_pattern(word), []
    for note in notes:
        for s in SENTENCE_END.split(" ".join(note.split())):
            if pat.search(s):
                w = s.split()
                if len(w) > MAX_WORDS:
                    i = next(k for k, t in enumerate(w) if pat.search(t))
                    w = w[max(0, i - WINDOW): i + WINDOW + 1]
                    s = ("… " if i > WINDOW else "") + " ".join(w) + " …"
                if s not in found:
                    found.append(s)
    return sorted(found, key=lambda s: len(s.split()))[:n]


class Synth:
    def __init__(self, tts, rate, folder: Path):
        self.tts, self.rate, self.folder = tts, rate, folder / "clips"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.made = self.kept = 0
        self.failed = []

    def __call__(self, text, voice):
        key = f"{self.tts}|{voice}|{self.rate}\n{text}"
        clip = self.folder / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}.mp3"
        if clip.exists() and clip.stat().st_size > 0:
            self.kept += 1
        else:
            print(f"  {voice or self.tts}: {text[:70]}", flush=True)
            ok = voiceover.BACKENDS[self.tts](text, str(clip), voice=voice, rate=self.rate)
            if not (ok and clip.exists() and clip.stat().st_size > 0):
                if clip.exists():
                    clip.unlink()
                self.failed.append(text)
                return None
            self.made += 1
        return "data:audio/mpeg;base64," + base64.b64encode(clip.read_bytes()).decode()


def build(words_file: Path, out_dir: Path, *, tts, voice, rate, terms: dict, notes=(),
          sentences=None, reference_voice=None):
    settings, words = read_words(words_file)
    n_sent = int(sentences if sentences is not None else settings.get("sentences", 2))
    ref_default = reference_voice or settings.get("reference_voice")
    pairs = sorted(terms.items(), key=lambda kv: len(kv[0]), reverse=True)
    synth = Synth(tts, rate, out_dir)
    rows = []
    for w in words:
        word = w["word"]
        current = terms.get(word)
        spellings = []                                    # (spelling, label)
        for c in w["candidates"]:
            spellings.append((c, "current" if c == current else ""))
        if current is not None and current not in w["candidates"]:
            spellings.insert(0, (current, "current"))
        if word not in [s for s, _ in spellings]:
            spellings.append((word, "as written"))
        sents = sentences_with(word, notes, n_sent)
        ref_voice = w["reference_voice"] or ref_default
        ref = synth(word, ref_voice) if ref_voice and tts in ("edge", "silent") else None
        pat = word_pattern(word)
        cells = []
        for spelling, label in spellings:
            spoken = voiceover.clean_for_tts(spelling)        # the spelling itself, sent as it is
            alone = synth(spoken, voice)
            inside = [synth(voiceover.clean_for_tts(pat.sub(SLOT, s), pairs).replace(SLOT, spoken), voice)
                      for s in sents]
            cells.append({"spelling": spelling, "label": label, "alone": alone, "inside": inside})
        rows.append({"word": word, "current": current, "ref_voice": ref_voice if ref else None,
                     "ref": ref, "sentences": sents, "cells": cells})
    page = out_dir / f"{words_file.stem}_pronunciation.html"
    page.write_text(render(rows, words_file.name, tts, voice, rate), encoding="utf-8")
    return {"page": page, "words": len(rows), "made": synth.made, "kept": synth.kept, "failed": synth.failed}


def audio(src):
    return f'<audio controls preload="none" src="{src}"></audio>' if src else '<span class="fail">failed</span>'


def render(rows, source, tts, voice, rate):
    e = html.escape
    parts = []
    for r, row in enumerate(rows):
        w = e(row["word"])
        head = "".join(f"<th>in sentence {k + 1}</th>" for k in range(len(row["sentences"])))
        body = []
        for c in row["cells"]:
            default = "current" if row["current"] is not None else "as written"
            checked = " checked" if c["label"] == default else ""
            label = f' <span class="tag">{e(c["label"])}</span>' if c["label"] else ""
            inside = "".join(f"<td>{audio(a)}</td>" for a in c["inside"])
            body.append(f'<tr><td><label><input type="radio" name="w{r}" value="{e(c["spelling"])}"'
                        f' data-word="{w}"{checked}> {e(c["spelling"])}</label>{label}</td>'
                        f'<td>{audio(c["alone"])}</td>{inside}</tr>')
        ref = (f'<p class="ref">As written, read by <code>{e(row["ref_voice"])}</code>: {audio(row["ref"])}</p>'
               if row["ref"] else "")
        sents = "".join(f"<li>{e(s)}</li>" for s in row["sentences"])
        sents = f'<ol class="sent">{sents}</ol>' if sents else '<p class="note">No sentence in the notes contains this word.</p>'
        parts.append(f'<section><h2>{w}</h2>{ref}<table><tr><th>spelling</th><th>alone</th>{head}</tr>'
                     f'{"".join(body)}</table>{sents}</section>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pronunciation test: {e(source)}</title>
<style>
body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 1100px; padding: 20px 28px 140px; color: #1d232c; }}
h1 {{ font-size: 24px; }} h2 {{ font-size: 20px; margin: 28px 0 6px; }}
table {{ border-collapse: collapse; }} th, td {{ text-align: left; padding: 4px 10px 4px 0; vertical-align: middle; }}
th {{ font-weight: 600; font-size: 13px; color: #5E6773; }}
audio {{ height: 32px; width: 210px; }}
.tag {{ font-size: 12px; background: #E6E0F0; color: #5A4A86; border-radius: 9px; padding: 1px 8px; }}
.ref {{ margin: 4px 0 8px; }} .sent {{ font-size: 14px; color: #3E4A5A; margin: 6px 0; }}
.note {{ font-size: 14px; color: #5E6773; }} .fail {{ color: #9A3B12; }}
#out {{ position: fixed; left: 0; right: 0; bottom: 0; background: #fbfaf6; border-top: 3px solid #2F5D8A;
  padding: 8px 28px; display: flex; gap: 12px; align-items: center; }}
#json {{ flex: 1; font: 13px ui-monospace, monospace; height: 54px; }}
</style>
</head>
<body>
<h1>Pronunciation test: {e(source)}</h1>
<p>Voice <code>{e(voice or tts)}</code> ({e(tts)}, rate {e(rate)}), {date.today().isoformat()}.
Listen, choose one spelling per word, and copy the choices into a terms file. A word chosen
"as written" needs no entry (remove it from the terms file if it has one).</p>
{"".join(parts)}
<div id="out"><textarea id="json" readonly></textarea><button id="copy">Copy JSON</button></div>
<script>
function update() {{
  const out = {{}};
  document.querySelectorAll('input[type=radio]:checked').forEach(r => {{
    if (r.value !== r.dataset.word) out[r.dataset.word] = r.value;
  }});
  document.getElementById('json').value = JSON.stringify(out, null, 1);
}}
document.querySelectorAll('input[type=radio]').forEach(r => r.addEventListener('change', update));
document.getElementById('copy').onclick = () => {{
  const t = document.getElementById('json'); t.select();
  try {{ navigator.clipboard.writeText(t.value); }} catch (e) {{ document.execCommand('copy'); }}
}};
update();
</script>
</body>
</html>
"""
