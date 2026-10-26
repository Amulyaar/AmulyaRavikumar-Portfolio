export const CATEGORIES = [
  { id: "home", name: "Home", icon: "⌂", color: "#d9e7ce", tags: ["small-space", "natural materials", "storage", "soft lighting", "slow living"] },
  { id: "style", name: "Style", icon: "◒", color: "#f2d1c6", tags: ["everyday", "minimal", "layering", "color", "recycled"] },
  { id: "tech", name: "Tech", icon: "⌘", color: "#d7d8f3", tags: ["useful tech", "audio", "desk setup", "smart home", "repairable"] },
  { id: "books", name: "Books", icon: "▤", color: "#ead8b6", tags: ["design", "wellbeing", "fiction", "food writing", "creative work"] },
  { id: "outdoors", name: "Outdoors", icon: "△", color: "#cde4df", tags: ["trail-ready", "weekend", "durable", "lightweight", "reusable"] },
  { id: "beauty", name: "Beauty", icon: "✳", color: "#f0d5e2", tags: ["gentle", "fragrance-free", "daily ritual", "refillable", "plant-based"] },
  { id: "food", name: "Food", icon: "◉", color: "#f3e0b5", tags: ["pantry", "fermentation", "coffee", "quick meals", "local makers"] },
  { id: "design", name: "Design", icon: "✷", color: "#d7e2ee", tags: ["graphic", "craft", "color study", "independent", "collectible"] },
  { id: "travel", name: "Travel", icon: "↗", color: "#d7e7ed", tags: ["packable", "city guide", "weekend", "carry-on", "local"] },
  { id: "wellness", name: "Wellness", icon: "≈", color: "#d7e7d5", tags: ["rest", "movement", "mindful", "recovery", "daily ritual"] }
];

const TITLES = {
  home: ["The modular bedside shelf", "Soft light for slow evenings", "A better way to store the little things", "The linen table edit", "Objects for a calmer corner"],
  style: ["The everyday layer, reworked", "A color that goes everywhere", "A better bag for the in-between", "Small-run pieces with a long life", "The weekend uniform"],
  tech: ["A quieter desk, one cable at a time", "Pocket audio for long walks", "The smart plug with a simple job", "A lamp that learns your routine", "Useful tech, made repairable"],
  books: ["A field guide to noticing more", "Stories from the edge of the map", "The illustrated guide to good food", "A small book about big ideas", "Notes on making things well"],
  outdoors: ["The daypack built for the long way", "A light that earns its place", "Weekend layers for changing weather", "The reusable bottle that travels", "Trail tools for curious people"],
  beauty: ["The gentle daily reset", "A refill for the five-minute ritual", "A little care for dry winter days", "Less scent, more softness", "The everyday essentials edit"],
  food: ["A brighter pantry, in three jars", "Coffee for the slow morning", "The quick dinner starter kit", "A local maker’s finishing oil", "Small-batch things worth sharing"],
  design: ["A print that changes with the light", "Color studies for quiet rooms", "The handmade cup, reimagined", "A playful object for the shelf", "Independent design, close up"],
  travel: ["The carry-on kit that packs flat", "A pocket guide to the side streets", "Objects for the two-day escape", "A city notebook for wanderers", "The packable layer, perfected"],
  wellness: ["A softer start to the morning", "Recovery tools for everyday movement", "A small ritual for switching off", "The stretch kit that lives by the door", "Rest, made a little easier"]
};

const MAKERS = ["Morrow Studio", "Common Practice", "Field Notes Co.", "Soft Form", "Good Things Lab", "Open House", "Northline", "Sunday Objects", "Kindred Supply", "Small Hours"];

function randomFor(seed) {
  let state = seed >>> 0;
  return function () {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function generateCatalog(size = 10000) {
  const items = new Array(size);
  for (let index = 0; index < size; index += 1) {
    const random = randomFor(index + 202509);
    const category = CATEGORIES[Math.floor(random() * CATEGORIES.length)];
    const titleOptions = TITLES[category.id];
    const tag = category.tags[Math.floor(random() * category.tags.length)];
    const ageDays = Math.floor(random() * 180);
    items[index] = {
      id: "ITEM-" + String(index + 1).padStart(5, "0"),
      category: category.id,
      categoryName: category.name,
      icon: category.icon,
      color: category.color,
      title: titleOptions[Math.floor(random() * titleOptions.length)],
      maker: MAKERS[Math.floor(random() * MAKERS.length)],
      tags: [tag, category.tags[Math.floor(random() * category.tags.length)]],
      price: Math.round((12 + random() * 188) * 100) / 100,
      freshness: Math.max(0.12, 1 - ageDays / 210),
      ageDays,
      popularity: 0.2 + random() * 0.8,
      quality: 0.58 + random() * 0.42
    };
  }
  return items;
}

export function scoreMatch(item, interests = []) {
  const selected = new Set(interests);
  let score = selected.has(item.category) ? 0.72 : 0.16;
  if (selected.size === 0) score = 0.48;
  if (item.tags.some(tag => selected.has(tag))) score += 0.12;
  return Math.min(1, score);
}

export function rankProducts(catalog, options = {}) {
  const {
    interests = [],
    strategy = "balanced",
    weights = { relevance: 62, freshness: 22, variety: 16 },
    blockedIds = [],
    limit = 8
  } = options;
  const blocked = new Set(blockedIds);
  const baseWeights = {
    match: { relevance: 1.25, freshness: 0.55, variety: 0.25 },
    fresh: { relevance: 0.95, freshness: 1.15, variety: 0.35 },
    balanced: { relevance: 1.0, freshness: 0.75, variety: 1.1 }
  }[strategy] || { relevance: 1, freshness: 0.75, variety: 0.8 };
  const relevanceWeight = Math.max(0, Number(weights.relevance) || 0) * baseWeights.relevance;
  const freshnessWeight = Math.max(0, Number(weights.freshness) || 0) * baseWeights.freshness;
  const varietyWeight = Math.max(0, Number(weights.variety) || 0) * baseWeights.variety;
  const denominator = Math.max(1, relevanceWeight + freshnessWeight + varietyWeight + 8);
  const ranked = [];
  const categoryCounts = new Map();
  const candidates = catalog.filter(item => !blocked.has(item.id));

  while (ranked.length < Math.min(limit, candidates.length)) {
    let bestIndex = -1;
    let bestScore = -Infinity;
    for (let index = 0; index < candidates.length; index += 1) {
      const item = candidates[index];
      if (!item) continue;
      const match = scoreMatch(item, interests);
      const categoryCount = categoryCounts.get(item.category) || 0;
      const novelty = 1 / (1 + categoryCount * 1.45);
      const score = (
        match * relevanceWeight +
        item.freshness * freshnessWeight +
        item.quality * 8 +
        novelty * varietyWeight
      ) / denominator;
      if (score > bestScore || (score === bestScore && item.id < candidates[bestIndex].id)) {
        bestIndex = index;
        bestScore = score;
      }
    }
    const item = candidates[bestIndex];
    const match = scoreMatch(item, interests);
    ranked.push({ ...item, match, score: bestScore, reason: buildReason(item, interests, strategy) });
    categoryCounts.set(item.category, (categoryCounts.get(item.category) || 0) + 1);
    candidates[bestIndex] = null;
  }
  return ranked;
}

function buildReason(item, interests, strategy) {
  if (interests.includes(item.category)) return "Matches your " + item.categoryName.toLowerCase() + " interest";
  if (strategy === "fresh") return "A fresh pick from the wider catalog";
  if (strategy === "balanced") return "A new lane to keep discovery varied";
  return "Related to your selected interests";
}

export function summarizeFeed(feed) {
  if (!feed.length) return { averageMatch: 0, categoryCoverage: 0, freshness: 0 };
  const categories = new Set(feed.map(item => item.category));
  const averageMatch = feed.reduce((sum, item) => sum + item.match, 0) / feed.length;
  const freshness = feed.reduce((sum, item) => sum + item.freshness, 0) / feed.length;
  return {
    averageMatch: Math.round(averageMatch * 100),
    categoryCoverage: categories.size,
    freshness: Math.round(freshness * 100)
  };
}
