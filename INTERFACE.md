# What `voiceover` and `narrate build-deck` read

`voiceover` narrates either a PowerPoint deck (`.pptx`, notes from its speaker
notes) or a slides page (`.html`). This file says what a slides page must
contain. Anything else in the page is copied unchanged.

## Slides page

```html
<head>
  ...                                   <!-- copied into the narrated page -->
  <style> #stage { width: 1920px; height: 1080px; ... } </style>
</head>
<body>
<div id="stage">
  <section class="slide"> ... </section>
  <section class="slide title"> ... </section>
  ...
</div>
<div id="notes"> ... </div>
<script>
const NOTES = ["notes for slide 1", "notes for slide 2", ...];
...
</script>
```

| Part | Rule |
|---|---|
| `<head>` | Required. Everything before `</head>` goes into the narrated page. |
| Stage | `<div id="stage">` written exactly so. The stage is the text from it to `<div id="notes"`, which must follow it. |
| Slides | Every element in the stage whose class list contains the token `slide` (`class="slide"`, `class="slide title"`): the same elements the player finds with `querySelectorAll('.slide')`. Do not use the class `slide` for anything that is not a slide. |
| Size | Width and height from the first `#stage { ... width: Wpx; height: Hpx` rule, in that order; 1920 × 1080 if there is none. |
| Notes | A JSON array after `const NOTES = `, ending at the first `];` followed by a line break; one line is safest. One string per slide, in order; `""` for a slide with no narration. The number of strings must equal the number of slides. |
| Not narrated yet | A page that already contains `id="nv-audio"` is a narrated page and is refused. |

## Pronunciations

A JSON object `{"written": "spoken", ...}`, given with `--pronunciations`.
How the spoken text is made from a note, in this order:

1. Each key is replaced by its value, longest key first. Keys are literal and
   case-sensitive and match anywhere, also inside words, so a homograph needs a
   phrase key: `"Why read": "Why reed"`.
2. Built-in replacements (symbols such as `≈`, `→`).
3. Greek letters become words: `μ` → `mu`, `Γ` → `capital gamma`. So write
   `Γ`, not "capital Γ", which would be read "capital capital gamma".
4. Subscript digits become digits.
5. Accents are removed (Unicode NFKD, combining marks dropped).

`--preview` writes the spoken text to `<name>_spoken.txt` without making audio,
and marks any character still outside ASCII with `NOT SPOKEN WELL`.

With Edge voices, spelling is the only way to change pronunciation: Edge
ignores SSML phoneme tags.

## Clips

Clips are kept in `audio/clips/<hash>.mp3`. The hash is of the voice back-end,
voice, rate, `--max-chars`, `--join` and the spoken text. `audio/slide_NN.mp3`
is a copy for slide position `NN`, and `audio/slide_NN.txt` records what it was
made from. A clip is made again only when its spoken text or settings change,
or with `--resynth`. Inserting, removing or moving a slide does not remake the
other slides. `audio/clips/` keeps old versions; delete it to start again.

## Deck source (`narrate build-deck`)

A talk folder with `slides.html` and `notes/slide_NN.md` (NN from 01) is built
into a slides page of the form above:

```bash
narrate build-deck talks/my_talk --foot "Project · My talk"   # writes talks/my_talk/my_talk.html
```

| In `slides.html` | Becomes |
|---|---|
| `\( ... \)`, `\[ ... \]` | inline and centred SVG (MathJax, glyphs inside each formula); TeX macros from `[deck] macros` or `--macros` |
| `src="asset:F"` | the image `F` from `[deck] assets` or `--assets`, embedded as a data URI |
| an element whose class list contains `slide` | a slide, numbered in order; a footer `FOOT · k / N` is added before its closing tag unless it has `data-nofoot` |
| `notes/slide_NN.md` | the `NN`th string of `NOTES` (missing file: `""`) |

A source **without a frame** (no `<div id="notes"`) has only a `<head>` with
its own style and a `<body>` holding `<div id="stage">`. `build-deck` adds
narrate's frame: [`frame.css`](src/narrate/frame/frame.css) as a style before
the source's first style (stage and slide geometry, 1920 × 1080 scaled to the
window, the notes panel, the bar, print), and
[`frame.html`](src/narrate/frame/frame.html) after the stage (the notes panel,
shown at the right and below the slide in a narrow window, N toggles; the bar;
the navigation script: arrow keys, Page Up/Down, Home/End, click left third to
go back, `#k` in the address). The source's style sets everything else
(colours, type, padding, the `.foot` line), and can override the frame.

A source **with its own frame** keeps it; it must contain `const NOTES = [];`,
which is filled.

MathJax comes from the project's `node_modules` (`npm install mathjax-full`),
found from the folder of `narration.toml` or the current folder upwards; `node`
is needed only when the source has TeX.
