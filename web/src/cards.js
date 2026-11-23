// The cards pager: the poster and the other cards side by side, one in front, the next peeking in.
// Native scroll snapping does the physics (the platform's own momentum and rubber-banding), so a card
// can be flicked, grabbed mid-flight and thrown back like any scroll view. Tabs and arrow keys move it too.

import { reducedMotion } from './spring.js';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

export function createPager({ onChange }) {
  const track = document.getElementById('card-track');
  const pager = document.getElementById('pager');
  let cards = [];
  let tabs = [];
  let index = 0;
  let target = null; // set while a tap scrolls to a card: the choice is already made, the scroll is just catching up

  /** items: [{ id, label, name }]. Returns one canvas per item, in order. */
  function load(items) {
    cards = items.map((item, i) => {
      const fig = el('figure', 'card');
      fig.dataset.card = item.id;
      fig.setAttribute('aria-roledescription', 'slide');
      fig.setAttribute('aria-label', `${i + 1} of ${items.length}: ${item.name}`);
      const canvas = el('canvas');
      canvas.width = 1080;
      canvas.height = 1920;
      canvas.setAttribute('role', 'img');
      fig.append(canvas);
      // A tap on the card peeking in at the side brings it to the front.
      fig.addEventListener('click', () => { if (i !== index) goTo(i); });
      return fig;
    });
    track.replaceChildren(...cards);
    tabs = items.map((item, i) => {
      const b = el('button', 'pager-tab', item.label);
      b.type = 'button';
      b.setAttribute('role', 'tab');
      b.addEventListener('click', () => goTo(i));
      b.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        const j = Math.max(0, Math.min(items.length - 1, index + (e.key === 'ArrowRight' ? 1 : -1)));
        goTo(j);
        tabs[j].focus();
      });
      return b;
    });
    pager.replaceChildren(...tabs);
    pager.hidden = items.length < 2;
    index = 0;
    target = null;
    sync(true);
    return cards.map((c) => c.querySelector('canvas'));
  }

  const step = () => (cards.length > 1 ? cards[1].offsetLeft - cards[0].offsetLeft : 0) || 1; // 1 while hidden

  // Cards that are leaving recede a little, the way the story's slides do.
  function paint(pos) {
    cards.forEach((c, i) => {
      const d = Math.min(1, Math.abs(pos - i));
      c.style.setProperty('--recede', String(d));
    });
  }

  function sync(force = false) {
    const pos = track.scrollLeft / step();
    paint(pos);
    if (target !== null && !force) {
      if (Math.abs(pos - target) < 0.02) target = null; // arrived
      return;
    }
    select(Math.max(0, Math.min(cards.length - 1, Math.round(pos))), force);
  }

  // Which card is in front: what Save saves and what the options under it are for.
  function select(i, force = false) {
    if (i === index && !force) return;
    index = i;
    tabs.forEach((t, k) => {
      t.setAttribute('aria-selected', String(k === i));
      t.tabIndex = k === i ? 0 : -1;
    });
    cards.forEach((c, k) => c.classList.toggle('is-current', k === i));
    onChange(i);
  }

  function goTo(i) {
    const card = cards[i];
    if (!card) return;
    // Commit at the tap (a quick tap on a tab and then Save saves that card), and let the scroll follow.
    target = reducedMotion.matches ? null : i;
    select(i);
    track.scrollTo({
      left: i * step(),
      behavior: reducedMotion.matches ? 'auto' : 'smooth',
    });
    if (reducedMotion.matches) sync();
  }

  track.addEventListener('scroll', () => sync(), { passive: true });
  // A finger on the track takes over from a tap's scroll, so the card follows the finger again.
  for (const ev of ['pointerdown', 'wheel', 'touchstart']) track.addEventListener(ev, () => { target = null; }, { passive: true });
  track.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    goTo(index + (e.key === 'ArrowRight' ? 1 : -1));
  });
  window.addEventListener('resize', () => { if (cards.length) track.scrollLeft = index * step(); });

  return {
    load,
    goTo,
    reset() { target = null; track.scrollLeft = 0; sync(true); },
    get index() { return index; },
  };
}
