(() => {
  const panel = document.getElementById("e3-provenance");
  if (!panel) return;

  const nameSlot = panel.querySelector("[data-provenance-name]");
  const spanSlot = panel.querySelector("[data-provenance-span]");
  const dateSlot = panel.querySelector("[data-provenance-date]");
  const buttons = document.querySelectorAll("[data-source-doc]");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      panel.dataset.selectedSource = button.dataset.sourceDoc;
      nameSlot.textContent = button.dataset.sourceLabel;
      spanSlot.textContent = button.dataset.sourceSpan;
      dateSlot.textContent = button.dataset.asOf;
    });
  });
})();
