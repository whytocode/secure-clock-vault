const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../assets/site.js"), "utf8");

function fixture(clipboard) {
  let activeElement = null;
  function element(properties = {}) {
    return {
      hidden: false, value: "", textContent: "", dataset: {}, attributes: {}, listeners: {},
      ...properties,
      addEventListener(type, listener) { this.listeners[type] = listener; },
      setAttribute(name, value) { this.attributes[name] = value; },
      focus() { activeElement = this; },
      select() { this.selected = true; },
      async emit(type) { await this.listeners[type](); }
    };
  }
  const filters = ["all", "library", "media", "tools"].map(category => element({ dataset: { category } }));
  const cards = [
    element({ textContent: "Grid and split view for images", dataset: { categories: "media" } }),
    element({ textContent: "Encrypted backup of files and folders", dataset: { categories: "tools" } }),
    element({ textContent: "Restore recycled files and folders", dataset: { categories: "library tools" } })
  ];
  const controls = element({ hidden: true, querySelectorAll: () => filters });
  const elements = new Map([
    ["feature-controls", controls], ["feature-search", element()], ["feature-reset", element()],
    ["feature-results", element()], ["feature-empty", element({ hidden: true })],
    ["apk-checksum", element({ value: "a3b30a903fdc665e" })], ["copy-status", element()]
  ]);
  const copy = element({ hidden: true, dataset: { copy: "apk-checksum" } });
  const document = {
    getElementById: id => elements.get(id) ?? null,
    querySelectorAll: () => cards,
    querySelector: () => copy
  };
  vm.runInNewContext(source, { document, navigator: { clipboard } });
  return {
    cards, filters, controls, copy,
    get: id => elements.get(id),
    active: () => activeElement,
    visible: () => cards.filter(card => !card.hidden),
    async search(value) {
      elements.get("feature-search").value = value;
      await elements.get("feature-search").emit("input");
    }
  };
}

test("all features start visible and controls progressively activate", () => {
  const page = fixture();
  assert.equal(page.controls.hidden, false);
  assert.equal(page.visible().length, 3);
  assert.equal(page.get("feature-empty").hidden, true);
  assert.match(page.get("feature-results").textContent, /^3 of 3/);
  assert.deepEqual(page.filters.map(button => button.attributes["aria-pressed"]), ["true", "false", "false", "false"]);
});

test("search is case-insensitive, trimmed, and matches all words in any order", async () => {
  const page = fixture();
  await page.search("  FOLDERS   encrypted  ");
  assert.deepEqual(page.visible(), [page.cards[1]]);
  assert.match(page.get("feature-results").textContent, /^1 of 3/);
  await page.search("   ");
  assert.equal(page.visible().length, 3);
});

test("category and search combine; empty results and reset remain actionable", async () => {
  const page = fixture();
  await page.filters[3].emit("click");
  assert.deepEqual(page.visible(), [page.cards[1], page.cards[2]]);
  await page.search("split");
  assert.equal(page.visible().length, 0);
  assert.equal(page.get("feature-empty").hidden, false);
  assert.match(page.get("feature-results").textContent, /^0 of 3/);
  assert.equal(page.filters[3].attributes["aria-pressed"], "true");
  await page.get("feature-reset").emit("click");
  assert.equal(page.get("feature-search").value, "");
  assert.equal(page.visible().length, 3);
  assert.equal(page.get("feature-empty").hidden, true);
  assert.equal(page.active(), page.get("feature-search"));
  assert.equal(page.filters[0].attributes["aria-pressed"], "true");
  assert.equal(page.filters[3].attributes["aria-pressed"], "false");
});

test("markup-like queries are plain search text, not rendered HTML", async () => {
  const page = fixture();
  await page.search("<img src=x onerror=alert(1)>");
  assert.equal(page.visible().length, 0);
  assert.equal(page.cards.some(card => Object.hasOwn(card, "innerHTML")), false);
  assert.equal(page.get("feature-results").textContent.includes("<img"), false);
});

test("checksum copying preserves success and explicit manual fallback", async () => {
  let copied = null;
  const allowed = fixture({ writeText: async value => { copied = value; } });
  await allowed.copy.emit("click");
  assert.equal(copied, allowed.get("apk-checksum").value);
  assert.equal(allowed.get("copy-status").textContent, "Checksum copied.");
  for (const clipboard of [undefined, { writeText: async () => { throw new Error("Permission denied"); } }]) {
    const denied = fixture(clipboard);
    await denied.copy.emit("click");
    assert.equal(denied.active(), denied.get("apk-checksum"));
    assert.equal(denied.get("apk-checksum").selected, true);
    assert.match(denied.get("copy-status").textContent, /blocked.*copy it manually/);
  }
});

test("pages without enhanced controls require no feature or clipboard DOM", () => {
  vm.runInNewContext(source, {
    document: { getElementById: () => null, querySelector: () => null }
  });
});
