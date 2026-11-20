// tex_svg.mjs - typeset TeX as self-contained SVG with MathJax (mathjax-full 3).
//
// Reads {"macros": {...}, "items": [{"tex": "...", "display": true|false}, ...]}
// on stdin and writes a JSON array of SVG strings, in the same order, on stdout.
// Each SVG carries its own glyph paths (fontCache "local"), so it can be pasted
// into a page with no script, font or stylesheet: `narrate build-deck` puts the
// formulas into a slides page this way, and the page works offline.
//
// MathJax is loaded from the node_modules in the folder given by the
// environment variable NARRATE_NODE_BASE (the project's own `npm install
// mathjax-full`), not from beside this file, which lives inside the installed
// Python package.
//
// From billpage/oziewicz src/narration/tex_svg.mjs (2026-11-17), with the macros
// moved out to the project and the module lookup changed. MIT licence.

import { createRequire } from 'node:module';
import path from 'node:path';

const base = process.env.NARRATE_NODE_BASE || process.cwd();
const require = createRequire(path.join(base, 'narrate-tex-svg.js'));
const { mathjax } = require('mathjax-full/js/mathjax.js');
const { TeX } = require('mathjax-full/js/input/tex.js');
const { SVG } = require('mathjax-full/js/output/svg.js');
const { liteAdaptor } = require('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = require('mathjax-full/js/handlers/html.js');
const { AllPackages } = require('mathjax-full/js/input/tex/AllPackages.js');

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  const { macros = {}, items } = JSON.parse(raw);
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const doc = mathjax.document('', {
    InputJax: new TeX({ packages: AllPackages.filter((p) => p !== 'colorv2'), macros }),
    OutputJax: new SVG({ fontCache: 'local' }),
  });
  const out = items.map(({ tex, display }, k) => {
    const node = doc.convert(tex, { display: !!display });
    const svg = adaptor.firstChild(node);
    const err = adaptor.innerHTML(node).match(/data-mjx-error="([^"]*)"/);
    if (err) {
      throw new Error(`TeX error "${err[1]}" in: ${tex}`);
    }
    // Text colour comes from the slide; the SVG uses currentColor. Glyph ids
    // are made unique per formula, so that no <use> refers to a glyph defined
    // in another formula (perhaps on a hidden slide).
    return adaptor.outerHTML(svg)
      .replace(/id="MJX-/g, `id="F${k}-MJX-`)
      .replace(/href="#MJX-/g, `href="#F${k}-MJX-`);
  });
  process.stdout.write(JSON.stringify(out));
});
