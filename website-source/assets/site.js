"use strict";

const featureControls = document.getElementById("feature-controls");
if (featureControls) {
  const search = document.getElementById("feature-search");
  const filters = [...featureControls.querySelectorAll("[data-category]")];
  const cards = [...document.querySelectorAll("[data-feature-card]")].map(element => ({
    element,
    text: element.textContent.toLowerCase(),
    categories: element.dataset.categories.split(/\s+/)
  }));
  const results = document.getElementById("feature-results");
  const empty = document.getElementById("feature-empty");
  let category = "all";

  function filterFeatures() {
    const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const card of cards) {
      const matches = (category === "all" || card.categories.includes(category))
        && words.every(word => card.text.includes(word));
      card.element.hidden = !matches;
      if (matches) visible += 1;
    }
    for (const button of filters) {
      button.setAttribute("aria-pressed", String(button.dataset.category === category));
    }
    results.textContent = `${visible} of ${cards.length} features shown. Search stays in your browser.`;
    empty.hidden = visible !== 0;
  }

  search.addEventListener("input", filterFeatures);
  for (const button of filters) {
    button.addEventListener("click", () => {
      category = button.dataset.category;
      filterFeatures();
    });
  }
  document.getElementById("feature-reset").addEventListener("click", () => {
    search.value = "";
    category = "all";
    filterFeatures();
    search.focus();
  });
  filterFeatures();
  featureControls.hidden = false;
}

const copyButton = document.querySelector("[data-copy]");
if (copyButton) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    const input = document.getElementById(copyButton.dataset.copy);
    const status = document.getElementById("copy-status");
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard access is unavailable.");
      }
      await navigator.clipboard.writeText(input.value);
      status.textContent = "Checksum copied.";
    } catch {
      input.focus();
      input.select();
      status.textContent = "Clipboard access was blocked. The checksum is selected; copy it manually.";
    }
  });
}
