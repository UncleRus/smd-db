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

/**
 * Package drawing tooltip.
 *
 * Every package code in a list carries data-pkg-image, the URL of the single
 * package-image endpoint. While the pointer is over a code that URL is shown in
 * one tooltip: the endpoint serves the drawing, or a placeholder when the
 * package has none. The tooltip is pinned with `position: fixed`, so the
 * scrollable table wrapper never clips it.
 */
(function () {
  var tip = document.querySelector(".smd-pkg-tip");
  if (!tip) {
    return;
  }
  var image = tip.querySelector(".smd-pkg-tip-image");
  var currentUrl = "";

  function place(target) {
    var rect = target.getBoundingClientRect();
    var gap = 8;
    var viewport = document.documentElement.clientWidth;
    var left = rect.left + rect.width / 2 - tip.offsetWidth / 2;
    left = Math.max(gap, Math.min(left, viewport - tip.offsetWidth - gap));
    var top = rect.top - tip.offsetHeight - gap;
    if (top < gap) {
      top = rect.bottom + gap;
    }
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }

  function show(target) {
    var url = target.getAttribute("data-pkg-image");
    if (!url) {
      return;
    }
    if (url !== currentUrl) {
      image.src = url;
      currentUrl = url;
    }
    tip.hidden = false;
    place(target);
  }

  function hide() {
    tip.hidden = true;
  }

  document.addEventListener("mouseover", function (event) {
    if (!(event.target instanceof Element)) {
      return;
    }
    var target = event.target.closest("[data-pkg-image]");
    if (target && !target.contains(event.relatedTarget)) {
      show(target);
    }
  });

  document.addEventListener("mouseout", function (event) {
    if (!(event.target instanceof Element)) {
      return;
    }
    var target = event.target.closest("[data-pkg-image]");
    if (target && !target.contains(event.relatedTarget)) {
      hide();
    }
  });

  // Fixed coordinates go stale as soon as the page moves.
  window.addEventListener("scroll", hide, true);
  window.addEventListener("resize", hide);
})();
