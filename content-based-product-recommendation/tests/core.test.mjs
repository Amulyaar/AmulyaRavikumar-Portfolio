import test from "node:test";
import assert from "node:assert/strict";
import { generateCatalog, rankProducts, summarizeFeed } from "../recommendation-core.mjs";

test("catalog generation returns the requested number of stable, unique items", () => {
  const first = generateCatalog(10000);
  const second = generateCatalog(10000);
  assert.equal(first.length, 10000);
  assert.equal(new Set(first.map(item => item.id)).size, 10000);
  assert.deepEqual(first.slice(0, 12), second.slice(0, 12));
});

test("ranking is deterministic and returns unique items", () => {
  const catalog = generateCatalog(240);
  const options = { interests: ["home", "design"], strategy: "balanced", limit: 8 };
  const first = rankProducts(catalog, options);
  const second = rankProducts(catalog, options);
  assert.deepEqual(first.map(item => item.id), second.map(item => item.id));
  assert.equal(new Set(first.map(item => item.id)).size, 8);
});

test("balanced ranking can broaden category coverage versus strict match", () => {
  const catalog = Array.from({ length: 9 }, (_, index) => ({
    id: "ITEM-" + index,
    category: index === 8 ? "beauty" : "home",
    categoryName: index === 8 ? "Beauty" : "Home",
    tags: [],
    freshness: 0.5,
    quality: 0.8
  }));
  const interests = ["home"];
  const strict = rankProducts(catalog, {
    interests, strategy: "match", weights: { relevance: 85, freshness: 0, variety: 0 }, limit: 5
  });
  const balanced = rankProducts(catalog, {
    interests, strategy: "balanced", weights: { relevance: 20, freshness: 0, variety: 100 }, limit: 5
  });
  assert.ok(summarizeFeed(balanced).categoryCoverage > summarizeFeed(strict).categoryCoverage);
});

test("hidden items do not appear in the next ranking", () => {
  const catalog = generateCatalog(100);
  const hidden = new Set(catalog.slice(0, 10).map(item => item.id));
  const feed = rankProducts(catalog, { interests: ["tech"], blockedIds: [...hidden], limit: 8 });
  assert.equal(feed.length, 8);
  assert.ok(feed.every(item => !hidden.has(item.id)));
});

test("feed summary reports bounded percentages and distinct categories", () => {
  const feed = rankProducts(generateCatalog(120), { interests: ["books"], limit: 8 });
  const summary = summarizeFeed(feed);
  assert.ok(summary.averageMatch >= 0 && summary.averageMatch <= 100);
  assert.ok(summary.freshness >= 0 && summary.freshness <= 100);
  assert.ok(summary.categoryCoverage >= 1 && summary.categoryCoverage <= 8);
});
