const toggles = document.querySelectorAll('.case-toggle');
toggles.forEach(button => button.addEventListener('click', () => {
  const detail = document.getElementById(button.getAttribute('aria-controls'));
  const open = button.getAttribute('aria-expanded') === 'true';
  button.setAttribute('aria-expanded', String(!open));
  detail.hidden = open;
  if (!open) detail.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
}));

const menuButton = document.querySelector('.menu-button');
const mobileMenu = document.getElementById('mobile-menu');
menuButton.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!open));
  menuButton.setAttribute('aria-label', open ? 'Open menu' : 'Close menu');
  mobileMenu.hidden = open;
});
mobileMenu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  mobileMenu.hidden = true;
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.setAttribute('aria-label', 'Open menu');
}));

const samples = [
  {title:'Thirty-second weeknight cooking',topic:'Food',emoji:'🍳',color:'#ffd6a9',relevance:92,freshness:61},
  {title:'Indie film finds from new voices',topic:'Film',emoji:'🎬',color:'#d7c5ff',relevance:81,freshness:73},
  {title:'A city through its night markets',topic:'Travel',emoji:'🌆',color:'#a8d9dd',relevance:72,freshness:95},
  {title:'The small-space design edit',topic:'Design',emoji:'✳',color:'#c7e7a0',relevance:69,freshness:88},
  {title:'What’s behind the viral recipe?',topic:'Food',emoji:'🥬',color:'#ffe3ae',relevance:88,freshness:90},
  {title:'An animation you may have missed',topic:'Film',emoji:'🎞',color:'#cfb9ff',relevance:79,freshness:85},
  {title:'A local maker’s studio tour',topic:'Design',emoji:'🪑',color:'#c7e7a0',relevance:73,freshness:67},
  {title:'A trail just beyond the city',topic:'Travel',emoji:'🏞',color:'#a8d9dd',relevance:67,freshness:80}
];
const sliderIds = ['relevance','freshness','diversity'];
const sliders = Object.fromEntries(sliderIds.map(id => [id,document.getElementById(id)]));
const feed = document.getElementById('feed-list');
const count = document.getElementById('topic-count');
function renderFeed(){
  const w = Object.fromEntries(sliderIds.map(id => [id,Number(sliders[id].value)]));
  sliderIds.forEach(id => document.getElementById(`${id}-value`).value = w[id]);
  const remaining = [...samples];
  const ranked = [];
  const chosenTopics = new Set();
  while (ranked.length < 5) {
    const rankedCandidates = remaining.map(item => ({item,score:(w.relevance*item.relevance + w.freshness*item.freshness + w.diversity*(chosenTopics.has(item.topic) ? 0 : 100))/Math.max(1,w.relevance+w.freshness+w.diversity)}));
    rankedCandidates.sort((a,b) => b.score-a.score || a.item.title.localeCompare(b.item.title));
    const best = rankedCandidates[0];
    ranked.push(best);
    chosenTopics.add(best.item.topic);
    remaining.splice(remaining.indexOf(best.item),1);
  }
  count.textContent = `${chosenTopics.size} DISTINCT TOPICS`;
  feed.replaceChildren(...ranked.map(({item,score},i) => {
    const row = document.createElement('li');
    const rank = document.createElement('span'); rank.className='feed-rank'; rank.textContent=String(i+1).padStart(2,'0');
    const icon = document.createElement('span'); icon.className='feed-icon'; icon.style.background=item.color; icon.textContent=item.emoji; icon.setAttribute('aria-hidden','true');
    const label = document.createElement('span'); label.className='feed-item-text';
    const title = document.createElement('strong'); title.textContent=item.title;
    const topic = document.createElement('small'); topic.textContent=item.topic;
    label.append(title,topic);
    const scoreTag = document.createElement('span'); scoreTag.className='feed-score'; scoreTag.textContent=String(Math.round(score)); scoreTag.setAttribute('aria-label',`Illustrative score ${Math.round(score)}`);
    row.append(rank,icon,label,scoreTag);
    return row;
  }));
}
sliderIds.forEach(id => sliders[id].addEventListener('input',renderFeed));
document.getElementById('reset-lab').addEventListener('click',() => {sliders.relevance.value=60;sliders.freshness.value=35;sliders.diversity.value=55;renderFeed()});
renderFeed();
