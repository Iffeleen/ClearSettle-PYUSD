// Feature tabs for the order page. No framework: show one panel, hide the rest.
(function () {
  var buttons = document.querySelectorAll(".tab-btn");
  var panels = document.querySelectorAll(".panel");
  if (!buttons.length) return;

  var storeKey = "tab:" + location.pathname;

  function show(name) {
    var found = false;
    buttons.forEach(function (b) {
      var on = b.dataset.tab === name;
      b.classList.toggle("active", on);
      if (on) found = true;
    });
    panels.forEach(function (p) {
      p.classList.toggle("active", p.id === "panel-" + name);
    });
    if (!found) return show("overview");
    try { sessionStorage.setItem(storeKey, name); } catch (e) {}
  }

  buttons.forEach(function (b) {
    b.addEventListener("click", function () { show(b.dataset.tab); });
  });
  document.querySelectorAll("[data-goto]").forEach(function (a) {
    a.addEventListener("click", function (e) { e.preventDefault(); show(a.dataset.goto); });
  });

  var start = "overview";
  try { start = sessionStorage.getItem(storeKey) || "overview"; } catch (e) {}
  // A freshly generated buyer link must be visible right away.
  if (document.getElementById("buyer-link")) start = "consent";
  show(start);
})();
