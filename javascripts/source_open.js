// Configuration: set to true to have source code admonitions open by default,
// false to have them closed by default.
const SOURCE_CODE_OPEN_BY_DEFAULT = true;

// Configuration: set to true to hide the admonition title/summary,
// false to show the title (e.g., "Source Code filename.py").
const SOURCE_CODE_HIDE_TITLE = true;

// Highlight keyword argument names (xxx in xxx=yyy patterns).
// Finds Name tokens immediately followed by '=' operator (no space) and adds a special class.
function highlightKeywordArgs(container) {
  const nameSpans = container.querySelectorAll('.highlight span.n');
  nameSpans.forEach(span => {
    const next = span.nextSibling;
    if (!next) return;
    if (next.nodeType === Node.TEXT_NODE) return;
    if (next.nodeType === Node.ELEMENT_NODE &&
        next.classList.contains('o') && next.textContent === '=') {
      span.classList.add('kwarg-name');
    }
  });
}

// Hide docstring lines in a code block.
// Pygments wraps each line in a span with id like "__span-0-14" (block-linenum).
// Docstring content is marked with class "sd" (string doc).
// We find docstring ranges and hide all lines within them, including empty lines.
function hideDocstringLines(details) {
  const table = details.querySelector('table.highlighttable');
  if (!table) return;

  const code = table.querySelector('td.code code');
  if (!code) return;

  const hiddenLineIds = new Set();
  const lineSpans = Array.from(code.querySelectorAll('span[id^="__span-"]'));

  let inDocstring = false;
  lineSpans.forEach(lineSpan => {
    const hasDocstring = lineSpan.querySelector('.sd');
    const lineText = lineSpan.textContent;

    if (hasDocstring) {
      inDocstring = true;
      lineSpan.style.display = 'none';
      const match = lineSpan.id.match(/__span-(\d+-\d+)/);
      if (match) {
        hiddenLineIds.add(match[1]);
      }
      if (lineText.match(/"""\s*$/) && lineText.match(/^\s*"""/)) {
        inDocstring = false;
      } else if (lineText.match(/"""\s*$/) && !lineText.match(/^\s*"""/)) {
        inDocstring = false;
      }
    } else if (inDocstring) {
      lineSpan.style.display = 'none';
      const match = lineSpan.id.match(/__span-(\d+-\d+)/);
      if (match) {
        hiddenLineIds.add(match[1]);
      }
    }
  });

  const linenosDiv = table.querySelector('td.linenos .linenodiv pre');
  if (!linenosDiv) return;

  const linenoSpans = Array.from(linenosDiv.querySelectorAll('span.normal'));
  linenoSpans.forEach(linenoSpan => {
    const anchor = linenoSpan.querySelector('a');
    if (!anchor) return;
    const href = anchor.getAttribute('href');
    if (!href) return;
    const lineId = href.replace('#__codelineno-', '');
    if (hiddenLineIds.has(lineId)) {
      const nextSibling = linenoSpan.nextSibling;
      if (nextSibling && nextSibling.nodeType === Node.TEXT_NODE) {
        nextSibling.remove();
      }
      linenoSpan.remove();
    }
  });
}

// Apply custom "sourcecode" admonition styling to mkdocstrings source code blocks.
//
// mkdocstrings-python renders source code in <details class="quote"> elements
// inside .doc-contents. This script:
//   1. Optionally opens them on page load (controlled by SOURCE_CODE_OPEN_BY_DEFAULT)
//   2. Replaces the "quote" class with "sourcecode" to apply custom styling
//      (magenta border and code icon, defined in extra.css)
//   3. Hides docstring lines from the displayed source code (since they're already
//      rendered as documentation above)
//
// Uses Material for MkDocs' document$ observable to handle instant navigation
// between pages.
document$.subscribe(() => {
  document.querySelectorAll('.doc-contents details.quote').forEach(details => {
    if (SOURCE_CODE_OPEN_BY_DEFAULT) {
      details.setAttribute('open', '');
    }
    details.classList.remove('quote');
    details.classList.add('sourcecode');

    const summary = details.querySelector('summary');
    if (summary) {
      if (SOURCE_CODE_HIDE_TITLE) {
        summary.classList.add('sourcecode-no-title');
      } else {
        const codeElement = summary.querySelector('code');
        if (codeElement) {
          const filename = codeElement.textContent;
          summary.textContent = '';
          summary.appendChild(document.createTextNode('Source Code '));
          summary.appendChild(codeElement);
        }
      }
    }

    // Hide docstring lines from the source code display
    hideDocstringLines(details);
  });

  // Highlight keyword argument names in all code blocks on the page
  highlightKeywordArgs(document);
});
