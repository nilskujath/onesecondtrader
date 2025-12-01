// Configuration: set to true to have source code admonitions open by default,
// false to have them closed by default.
const SOURCE_CODE_OPEN_BY_DEFAULT = false;

// Apply custom "sourcecode" admonition styling to mkdocstrings source code blocks.
//
// mkdocstrings-python renders source code in <details class="quote"> elements
// inside .doc-contents. This script:
//   1. Optionally opens them on page load (controlled by SOURCE_CODE_OPEN_BY_DEFAULT)
//   2. Replaces the "quote" class with "sourcecode" to apply custom styling
//      (magenta border and code icon, defined in extra.css)
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

    // Change header text from "Source code in `filename`" to "Code filename"
    const summary = details.querySelector('summary');
    if (summary) {
      const codeElement = summary.querySelector('code');
      if (codeElement) {
        const filename = codeElement.textContent;
        summary.textContent = '';
        summary.appendChild(document.createTextNode('Source Code '));
        summary.appendChild(codeElement);
      }
    }
  });
});
