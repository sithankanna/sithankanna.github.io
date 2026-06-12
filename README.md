# sithankanna.com

Static GitHub Pages site for `www.sithankanna.com` — my technical blog.

The site is plain HTML with a site-owned stylesheet. Math is written in LaTeX
and rendered in the browser by [MathJax](https://www.mathjax.org/); diagrams are
hand-authored SVG.

## Structure

```
index.html              Blog landing page (post listing)
posts/                  One HTML file per post
js/mathjax-config.js    Shared MathJax config; mirrors the \newcommand macros
                        from the source LaTeX so math can be pasted in verbatim
css/site.css            Stylesheet (incl. LaTeX-style section numbering)
assets/figures/         SVG diagrams
CNAME                   Custom domain
```

## Authoring a post

1. Copy an existing file in `posts/` as a starting point.
2. Write prose as HTML; write math in LaTeX using `\( … \)` (inline) and
   `\[ … \]` or `\begin{align} … \end{align}` (display). Custom macros live in
   `js/mathjax-config.js`.
3. Add diagrams as SVG under `assets/figures/` and reference them with
   `<figure class="fig">`.
4. Link the post from `index.html`.

Open any HTML file directly in a browser to preview.
