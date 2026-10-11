/* Studio enhancements. The editor works fully without JavaScript. */
(function () {
  "use strict";

  function slugify(text) {
    return text
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9\s-]/g, "")
      .trim()
      .replace(/[\s-]+/g, "-")
      .slice(0, 200)
      .replace(/^-+|-+$/g, "");
  }

  function initSlug(form) {
    var title = form.querySelector("#id_title");
    var slug = form.querySelector("#id_slug");
    if (!title || !slug) return;
    // Only auto-fill while the slug is empty or still matches the generated value.
    var auto = slug.value === "" || slug.value === slugify(title.value);
    var isPublished = !!form.querySelector(".badge--published");
    if (isPublished) auto = false; // never silently change a live URL
    slug.addEventListener("input", function () { auto = slug.value === ""; });
    title.addEventListener("input", function () {
      if (auto) slug.value = slugify(title.value);
    });
  }

  function initCounters(root) {
    root.querySelectorAll("[data-counter-for]").forEach(function (counter) {
      var input = document.getElementById(counter.getAttribute("data-counter-for"));
      var max = parseInt(counter.getAttribute("data-max"), 10);
      if (!input) return;
      function update() {
        var n = input.value.length;
        counter.textContent = n + " / " + max;
        counter.classList.toggle("is-over", n > max);
      }
      input.addEventListener("input", update);
      update();
    });
  }

  function initWordCount(form) {
    var body = form.querySelector("#id_body");
    var out = form.querySelector("[data-wordcount]");
    if (!body || !out) return;
    var timer;
    function update() {
      var words = body.value.trim() ? body.value.trim().split(/\s+/).length : 0;
      var minutes = Math.max(1, Math.ceil(words / 230));
      out.textContent = words + " words · about " + minutes + " min read. ";
    }
    body.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(update, 250);
    });
    update();
  }

  var FORMATS = {
    bold: { wrap: ["**", "**"], placeholder: "bold text" },
    italic: { wrap: ["*", "*"], placeholder: "italic text" },
    code: { wrap: ["`", "`"], placeholder: "code" },
    link: { wrap: ["[", "](https://)"], placeholder: "link text" },
    heading: { line: "## ", placeholder: "Heading" },
    subheading: { line: "### ", placeholder: "Subheading" },
    quote: { line: "> ", placeholder: "Quotation" },
    list: { line: "- ", placeholder: "List item" },
    numbered: { line: "1. ", placeholder: "List item" },
    rule: { block: "\n\n---\n\n" }
  };

  function applyFormat(textarea, name) {
    var f = FORMATS[name];
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var value = textarea.value;
    var selected = value.slice(start, end);
    var insert, cursorStart, cursorEnd;

    if (f.block) {
      insert = f.block;
      cursorStart = cursorEnd = start + insert.length;
    } else if (f.wrap) {
      var text = selected || f.placeholder;
      insert = f.wrap[0] + text + f.wrap[1];
      cursorStart = start + f.wrap[0].length;
      cursorEnd = cursorStart + text.length;
    } else {
      var lineStart = value.lastIndexOf("\n", start - 1) + 1;
      var block = value.slice(lineStart, end) || f.placeholder;
      insert = block.split("\n").map(function (line) { return f.line + line; }).join("\n");
      start = lineStart;
      cursorStart = start;
      cursorEnd = start + insert.length;
    }

    textarea.focus();
    textarea.setRangeText(insert, start, end, "end");
    textarea.setSelectionRange(cursorStart, cursorEnd);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function initToolbar(form) {
    var toolbar = form.querySelector("[data-md-toolbar]");
    var body = form.querySelector("#id_body");
    if (!toolbar || !body) return;
    toolbar.hidden = false;
    toolbar.addEventListener("click", function (event) {
      var button = event.target.closest("[data-md]");
      if (button) applyFormat(body, button.getAttribute("data-md"));
    });
    body.addEventListener("keydown", function (event) {
      if (!(event.ctrlKey || event.metaKey)) return;
      var key = event.key.toLowerCase();
      if (key === "b" || key === "i" || key === "k") {
        event.preventDefault();
        applyFormat(body, { b: "bold", i: "italic", k: "link" }[key]);
      }
    });
  }

  function initUnsavedWarning(form) {
    var dirty = false;
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("change", function () { dirty = true; });
    form.addEventListener("submit", function (event) {
      var submitter = event.submitter;
      // Previews open in a new tab and don't save, so keep the warning armed.
      if (!submitter || !submitter.hasAttribute("data-preview")) dirty = false;
    });
    window.addEventListener("beforeunload", function (event) {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  function initCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach(function (button) {
      button.hidden = false;
      button.addEventListener("click", function () {
        var input = document.getElementById(button.getAttribute("data-copy"));
        if (!input) return;
        input.select();
        var done = function () {
          var label = button.textContent;
          button.textContent = "Copied";
          setTimeout(function () { button.textContent = label; }, 1500);
        };
        if (navigator.clipboard) {
          navigator.clipboard.writeText(input.value).then(done, function () {});
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-editor]");
    if (form) {
      initSlug(form);
      initWordCount(form);
      initToolbar(form);
      initUnsavedWarning(form);
    }
    initCounters(document);
    initCopyButtons();
  });
})();
