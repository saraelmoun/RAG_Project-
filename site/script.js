/* Animations discretes au scroll : on revele les elements .reveal quand ils
   entrent dans le viewport. Degradation gracieuse : si IntersectionObserver
   n'existe pas (ou JS desactive via le HTML), les elements restent visibles. */
(function () {
  "use strict";

  var items = document.querySelectorAll(".reveal");

  // Repli : pas d'observer -> tout visible immediatement.
  if (!("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("visible"); });
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  items.forEach(function (el, i) {
    // petit decalage en cascade pour les elements d'une meme grille
    el.style.transitionDelay = (Math.min(i, 6) * 50) + "ms";
    observer.observe(el);
  });
})();

/* Terminal interactif : "▶ Exécuter" deroule le pipeline ligne par ligne.
   Sans JS / reduced-motion : les lignes restent visibles (fallback statique). */
(function () {
  "use strict";

  var term = document.querySelector(".run-term");
  var btn = document.getElementById("run-btn");
  if (!term || !btn) return;

  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { btn.style.display = "none"; return; }  // tout reste visible, pas d'anim

  var lines = Array.prototype.slice.call(term.querySelectorAll(".run-line"));
  var timers = [];

  function reset() {
    timers.forEach(clearTimeout);
    timers = [];
    lines.forEach(function (l) { l.classList.remove("show"); });
  }

  function run() {
    term.classList.add("armed");   // active le mode cache + barres a 0
    reset();
    btn.textContent = "■ En cours…";
    btn.disabled = true;
    lines.forEach(function (line, i) {
      timers.push(setTimeout(function () {
        line.classList.add("show");
        if (i === lines.length - 1) {
          btn.textContent = "↻ Rejouer";
          btn.disabled = false;
        }
      }, 550 * (i + 1)));
    });
  }

  btn.addEventListener("click", run);
})();
