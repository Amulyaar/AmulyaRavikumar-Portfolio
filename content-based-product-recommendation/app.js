import { CATEGORIES, generateCatalog, rankProducts, summarizeFeed } from "./recommendation-core.mjs";

const catalog = generateCatalog(10000);
const interestList = document.getElementById("interest-list");
const productGrid = document.getElementById("product-grid");
const status = document.getElementById("feed-status");
const toast = document.createElement("div");
toast.className = "toast";
toast.setAttribute("role", "status");
toast.setAttribute("aria-live", "polite");
document.body.append(toast);

const state = {
  interests: new Set(["design", "home", "tech"]),
  strategy: "match",
  hidden: new Set(),
  saved: new Set(),
  currentFeed: [],
  setNumber: 1
};

const sliderIds = ["relevance", "freshness", "variety"];
const sliders = Object.fromEntries(sliderIds.map(id => [id, document.getElementById(id)]));
const strategyNotes = {
  match: "Prioritizes shared categories and product attributes.",
  fresh: "Keeps relevance in view while giving newer products more room.",
  balanced: "Uses a light category-repeat penalty to open another discovery lane."
};

function announce(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(announce.timeout);
  announce.timeout = window.setTimeout(() => toast.classList.remove("show"), 1900);
}

function renderInterests() {
  interestList.replaceChildren(...CATEGORIES.map(category => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "interest-chip";
    button.textContent = category.name;
    button.setAttribute("aria-pressed", String(state.interests.has(category.id)));
    button.addEventListener("click", () => {
      if (state.interests.has(category.id)) {
        state.interests.delete(category.id);
      } else {
        state.interests.add(category.id);
      }
      state.setNumber = 1;
      state.hidden.clear();
      render();
    });
    return button;
  }));
}

function makeProductCard(item, index) {
  const card = document.createElement("li");
  card.className = "product-card";
  card.style.animationDelay = String(index * 35) + "ms";

  const art = document.createElement("div");
  art.className = "product-art";
  art.style.setProperty("--item-color", item.color);
  const rank = document.createElement("span");
  rank.className = "product-rank";
  rank.textContent = "MATCH " + String(index + 1).padStart(2, "0");
  const symbol = document.createElement("span");
  symbol.className = "item-art-symbol";
  symbol.textContent = item.icon;
  symbol.setAttribute("aria-hidden", "true");
  art.append(rank, symbol);

  const body = document.createElement("div");
  body.className = "product-body";
  const category = document.createElement("div");
  category.className = "product-category";
  const categoryName = document.createElement("span");
  categoryName.textContent = item.categoryName;
  const age = document.createElement("span");
  age.textContent = item.ageDays < 14 ? "NEW" : item.ageDays + "D AGO";
  category.append(categoryName, age);

  const title = document.createElement("h4");
  title.textContent = item.title;
  const maker = document.createElement("div");
  maker.className = "product-maker";
  maker.textContent = item.maker + " · " + item.tags[0];
  const reason = document.createElement("p");
  reason.className = "product-reason";
  reason.textContent = item.reason;
  const bottom = document.createElement("div");
  bottom.className = "product-bottom";
  const price = document.createElement("span");
  price.className = "product-price";
  price.textContent = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(item.price);
  const score = document.createElement("span");
  score.className = "product-score";
  score.textContent = Math.round(item.match * 100) + "% FIT";
  bottom.append(price, score);

  const actions = document.createElement("div");
  actions.className = "product-actions";
  const save = document.createElement("button");
  save.type = "button";
  save.className = state.saved.has(item.id) ? "saved" : "";
  save.textContent = state.saved.has(item.id) ? "Saved ✓" : "Save";
  save.setAttribute("aria-pressed", String(state.saved.has(item.id)));
  save.addEventListener("click", () => {
    if (state.saved.has(item.id)) {
      state.saved.delete(item.id);
      announce("Removed from this session’s saved items");
    } else {
      state.saved.add(item.id);
      state.interests.add(item.category);
      announce("Saved — added " + item.categoryName.toLowerCase() + " to your interests");
    }
    state.setNumber = 1;
    state.hidden.clear();
    render();
  });
  const hide = document.createElement("button");
  hide.type = "button";
  hide.textContent = "Hide";
  hide.setAttribute("aria-label", "Hide " + item.title + " for this session");
  hide.addEventListener("click", () => {
    state.hidden.add(item.id);
    announce("Hidden for this session");
    render();
  });
  actions.append(save, hide);
  body.append(category, title, maker, reason, bottom, actions);
  card.append(art, body);
  return card;
}

function render() {
  renderInterests();
  sliderIds.forEach(id => {
    document.getElementById(id + "-value").value = sliders[id].value;
  });

  const weights = Object.fromEntries(sliderIds.map(id => [id, Number(sliders[id].value)]));
  const ranked = rankProducts(catalog, {
    interests: [...state.interests],
    strategy: state.strategy,
    weights,
    blockedIds: [...state.hidden],
    limit: 8
  });
  state.currentFeed = ranked;
  productGrid.replaceChildren();

  if (ranked.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "You’ve hidden every item in this set. Reset the playground to start over.";
    productGrid.append(empty);
  } else {
    ranked.forEach((item, index) => productGrid.append(makeProductCard(item, index)));
  }

  document.querySelectorAll(".strategy-tab").forEach(tab => {
    const active = tab.dataset.strategy === state.strategy;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.getElementById("strategy-note").textContent = strategyNotes[state.strategy];
  document.getElementById("feed-count").textContent = "SET " + String(state.setNumber).padStart(2, "0") + " / TOP 8";

  const summary = summarizeFeed(ranked);
  document.getElementById("metric-match").textContent = summary.averageMatch + "%";
  document.getElementById("metric-coverage").textContent = summary.categoryCoverage + " / 10";
  document.getElementById("metric-freshness").textContent = summary.freshness + "%";
  status.textContent = "10K synthetic items · " + state.saved.size + " saved · " + state.hidden.size + " hidden this session";
}

document.querySelectorAll(".strategy-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    state.strategy = tab.dataset.strategy;
    state.setNumber = 1;
    state.hidden.clear();
    render();
  });
});

sliderIds.forEach(id => sliders[id].addEventListener("input", () => {
  state.setNumber = 1;
  state.hidden.clear();
  render();
}));

document.getElementById("reset-lab").addEventListener("click", () => {
  sliders.relevance.value = "62";
  sliders.freshness.value = "22";
  sliders.variety.value = "16";
  state.interests = new Set(["design", "home", "tech"]);
  state.strategy = "match";
  state.hidden.clear();
  state.saved.clear();
  state.setNumber = 1;
  announce("Playground reset");
  render();
});

document.getElementById("next-set").addEventListener("click", () => {
  state.currentFeed.forEach(item => state.hidden.add(item.id));
  state.setNumber += 1;
  if (state.hidden.size >= catalog.length - 8) {
    state.hidden.clear();
    state.setNumber = 1;
    announce("Back to the first set");
  }
  render();
});

document.getElementById("catalog-size").textContent = catalog.length.toLocaleString("en-US");
render();
