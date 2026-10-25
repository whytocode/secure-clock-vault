"use strict";

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
