// Shared MathJax v3 configuration for the blog.
// The `macros` block mirrors the \newcommand definitions in the source LaTeX
// so that the math in each post can be pasted in essentially verbatim.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    tags: "ams", // number align environments; enables \label / \eqref / \ref
    macros: {
      // Helpers
      rowbar: "\\rule[.5ex]{2em}{0.4pt}",
      T: "\\mathsf{T}",
      bm: ["{\\boldsymbol{#1}}", 1],

      // Bold matrices / vectors (named to avoid clashing with LaTeX builtins)
      A: "{\\bm{A}}", as: "{\\bm{a}}",
      B: "{\\bm{B}}", bs: "{\\bm{b}}",
      C: "{\\bm{C}}", cs: "{\\bm{c}}",
      D: "{\\bm{D}}", ds: "{\\bm{d}}",
      E: "{\\bm{E}}", es: "{\\bm{e}}",
      F: "{\\bm{F}}", fs: "{\\bm{f}}",
      G: "{\\bm{G}}", gs: "{\\bm{g}}",
      h: "{\\bm{h}}",
      I: "{\\bm{I}}", is: "{\\bm{i}}",
      J: "{\\bm{J}}", js: "{\\bm{j}}",
      K: "{\\bm{K}}", ks: "{\\bm{k}}",
      LB: "{\\bm{L}}", ls: "{\\bm{l}}",
      M: "{\\bm{M}}", ms: "{\\bm{m}}",
      N: "{\\bm{N}}", ns: "{\\bm{n}}",
      OB: "{\\bm{O}}", os: "{\\bm{o}}",
      PB: "{\\bm{P}}", ps: "{\\bm{p}}",
      Q: "{\\bm{Q}}", qs: "{\\bm{q}}",
      R: "{\\bm{R}}", rs: "{\\bm{r}}",
      SB: "{\\bm{S}}", ssmall: "{\\bm{s}}",
      ts: "{\\bm{t}}",
      U: "{\\bm{U}}", us: "{\\bm{u}}",
      V: "{\\bm{V}}", vs: "{\\bm{v}}",
      W: "{\\bm{W}}", ws: "{\\bm{w}}",
      X: "{\\bm{X}}", xs: "{\\bm{x}}",
      Y: "{\\bm{Y}}", ys: "{\\bm{y}}",
      Z: "{\\bm{Z}}", zs: "{\\bm{z}}"
    }
  },
  chtml: {
    scale: 1.0,
    displayAlign: "left",
    displayIndent: "0"
  },
  options: {
    // keep equation tags clickable for \eqref links
    renderActions: {}
  }
};
