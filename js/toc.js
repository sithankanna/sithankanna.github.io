// Lightweight table-of-contents scrollspy: highlights the sidebar link for
// whichever section is currently at the top of the viewport.
(function () {
  function init() {
    var links = Array.prototype.slice.call(
      document.querySelectorAll('.sidebar nav a[href^="#"]')
    );
    if (!links.length) return;

    var byId = {};
    var targets = [];
    links.forEach(function (a) {
      var id = decodeURIComponent(a.getAttribute("href").slice(1));
      var el = document.getElementById(id);
      if (el) {
        byId[id] = a;
        targets.push(el);
      }
    });
    if (!targets.length) return;

    var current = null;
    function setActive(id) {
      if (id === current) return;
      current = id;
      links.forEach(function (a) {
        a.classList.remove("active");
      });
      if (byId[id]) byId[id].classList.add("active");
    }

    function onScroll() {
      var offset = 120; // a little below the sticky header
      var activeId = targets[0].id;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i].getBoundingClientRect().top <= offset) {
          activeId = targets[i].id;
        } else {
          break;
        }
      }
      setActive(activeId);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    onScroll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
