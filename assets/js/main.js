// Header background after scrolling past the hero top
const header = document.querySelector(".site-header");
const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 40);
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

// Mobile menu
const burger = document.querySelector(".burger");
const nav = document.querySelector(".site-nav");
if (burger && nav) {
  burger.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    burger.setAttribute("aria-expanded", String(open));
  });
  nav.querySelectorAll("a").forEach((link) =>
    link.addEventListener("click", () => {
      nav.classList.remove("open");
      burger.setAttribute("aria-expanded", "false");
    })
  );
}

// Reveal-on-scroll
const revealed = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealed.forEach((el) => io.observe(el));
} else {
  revealed.forEach((el) => el.classList.add("visible"));
}

// Results strip: arrow buttons scroll by one card and disable at either end
document.querySelectorAll(".scroll-btn").forEach((btn) => {
  const strip = document.getElementById(btn.dataset.target);
  if (!strip) return;
  const dir = Number(btn.dataset.dir);
  const update = () => {
    const max = strip.scrollWidth - strip.clientWidth - 1;
    btn.disabled = dir < 0 ? strip.scrollLeft <= 0 : strip.scrollLeft >= max;
  };
  btn.addEventListener("click", () => {
    const card = strip.querySelector(".result");
    const step = card ? card.getBoundingClientRect().width + 24 : 320;
    strip.scrollBy({ left: dir * step, behavior: "smooth" });
  });
  strip.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  update();
});

// Current year in the footer
document.querySelectorAll("[data-year]").forEach((el) => {
  el.textContent = new Date().getFullYear();
});
