(() => {
  const panel = document.getElementById("e3-provenance");
  if (!panel) return;

  const documentSlot = panel.querySelector("[data-provenance-doc]");
  const spanSlot = panel.querySelector("[data-provenance-span]");
  const dateSlot = panel.querySelector("[data-provenance-date]");

  document.querySelectorAll(".e3-fact").forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      document.querySelectorAll(".e3-fact").forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      documentSlot.textContent = button.dataset.sourceDoc;
      spanSlot.textContent = button.dataset.sourceSpan;
      dateSlot.textContent = `As of ${button.dataset.asOf}`;
    });
  });
})();
