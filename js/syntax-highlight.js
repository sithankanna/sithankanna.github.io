(() => {
  const pythonKeywords = [
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "False", "None", "True",
  ].join("|");

  const tokenPattern = new RegExp(
    [
      "(#.*$)",
      "(\\\"(?:\\\\.|[^\\\"\\\\])*\\\"|'(?:\\\\.|[^'\\\\])*')",
      `(\\b(?:${pythonKeywords})\\b)`,
      "(\\b\\d[\\d_]*(?:\\.\\d[\\d_]*)?\\b)",
      "(\\b[A-Za-z_]\\w*(?=\\s*\\())",
      "(\\b(?:[A-Z][A-Za-z0-9_]*|[A-Z][A-Z0-9_]*)\\b)",
    ].join("|"),
    "gm",
  );

  const escapeHtml = (text) => text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

  document.querySelectorAll('pre.code-block code[data-language="python"]')
    .forEach((block) => {
      const source = block.textContent;
      let html = "";
      let cursor = 0;

      for (const match of source.matchAll(tokenPattern)) {
        html += escapeHtml(source.slice(cursor, match.index));

        const className = match[1] ? "syntax-comment"
          : match[2] ? "syntax-string"
            : match[3] ? "syntax-keyword"
              : match[4] ? "syntax-number"
                : match[5] ? "syntax-function"
                  : "syntax-name";

        html += `<span class="${className}">${escapeHtml(match[0])}</span>`;
        cursor = match.index + match[0].length;
      }

      html += escapeHtml(source.slice(cursor));
      block.innerHTML = html;
    });
})();
