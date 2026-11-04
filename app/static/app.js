"use strict";

/**
 * Set or remove a single query parameter on the current URL and reload.
 * Used by the sort, page-size and theme controls so that the whole query
 * string (and therefore a shareable search link) stays in the address bar.
 *
 * @param {string} key   Query parameter name.
 * @param {string} value New value; an empty string removes the parameter.
 */
function smdSetParam(key, value) {
  var url = new URL(window.location.href);
  if (value === null || value === undefined || value === "") {
    url.searchParams.delete(key);
  } else {
    url.searchParams.set(key, value);
  }
  if (key !== "page") {
    url.searchParams.delete("page");
  }
  window.location.href = url.toString();
}

window.smdSetParam = smdSetParam;

/**
 * Make a whole result row behave like a link.
 *
 * Rows carry a data-href attribute. A plain left click anywhere in the row
 * navigates to it, except on interactive elements (which keep their own
 * behaviour) and while text is being selected. The part-name link inside the
 * row stays a real anchor, so keyboard and modifier/middle clicks still work.
 *
 * @param {MouseEvent} event Click event delegated from the document.
 */
function smdRowNavigate(event) {
  if (event.defaultPrevented || event.button !== 0) {
    return;
  }
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }
  var target = event.target;
  if (!(target instanceof Element)) {
    return;
  }
  var row = target.closest("tr[data-href]");
  if (!row) {
    return;
  }
  if (target.closest("a, button, input, select, textarea, label")) {
    return;
  }
  var selection = window.getSelection();
  if (selection && selection.toString().length > 0) {
    return;
  }
  window.location.href = row.getAttribute("data-href");
}

document.addEventListener("click", smdRowNavigate);
