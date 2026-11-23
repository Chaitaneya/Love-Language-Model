// The reveal: one fact per screen, moved by finger, tap, button or arrow keys.
// The track is driven by a spring, so a slide can be grabbed and thrown back mid-flight.

import { spring, velocityTracker, project, rubberband, reducedMotion } from './spring.js';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function slideFor(fact, i, total) {
  const slide = el('article', `slide slide-${fact.bigStyle || 'rows'}`);
  slide.setAttribute('aria-roledescription', 'slide');
  slide.setAttribute('aria-label', `${i + 1} of ${total}`);
  const inner = el('div', 'slide-inner');
  const main = el('div', 'slide-main');
  main.append(el('p', 'kicker', fact.kicker));

  if (fact.visual && fact.visual.kind === 'monologue') {
    main.append(monologue(fact.visual));
  }
  if (fact.visual && fact.visual.kind === 'gap') {
    main.append(gap(fact.visual));
  }
  if (fact.rows) {
    const rows = el('div', 'rows');
    for (const r of fact.rows) {
      const row = el('div', r.accent ? 'row-fact is-accent' : 'row-fact');
      row.append(el('span', 'row-name', r.name), el('span', 'row-value', r.value));
      rows.append(row);
    }
    main.append(rows);
  } else {
    main.append(el('h2', `big big-${fact.bigStyle}`, fact.big));
  }
  main.append(el('p', 'line', fact.line));

  const how = el('div', 'how-we-know');
  how.append(el('p', 'how-label', 'How we know'), el('p', 'how-text', fact.how));
  inner.append(main, how);
  slide.append(inner);
  return slide;
}

// One bar per message of the run, each as long as the real message was, then the reply in red:
// the poster's motif, in small. Long runs get thinner bars so the column keeps its height.
function monologue({ lens, n, reply }) {
  const wrap = el('div', 'mono');
  wrap.setAttribute('aria-hidden', 'true');
  const col = el('div', 'mono-col');
  col.style.setProperty('--bar', `${Math.max(1.5, Math.min(5, 150 / (n * 1.5)))}px`);
  const longest = Math.max(1, ...lens);
  for (let i = 0; i < n; i++) {
    const bar = el('span', 'mono-bar');
    bar.style.setProperty('--w', `${Math.round(12 + 88 * Math.sqrt((lens[i] ?? 0) / longest))}%`);
    col.append(bar);
  }
  wrap.append(col, el('span', 'mono-reply', reply));
  return wrap;
}

// The busiest day, then the empty days, then the day someone wrote again.
function gap({ from, to, days }) {
  const wrap = el('div', 'gap');
  wrap.setAttribute('aria-hidden', 'true');
  const dots = el('div', 'gap-dots');
  dots.append(el('span', 'gap-dot is-on'));
  for (let i = 0; i < Math.min(days, 30); i++) dots.append(el('span', 'gap-dot'));
  dots.append(el('span', 'gap-dot is-on'));
  const ends = el('div', 'gap-ends');
  ends.append(el('span', null, from), el('span', null, to));
  wrap.append(dots, ends);
  return wrap;
}

export function createReveal({ onDone }) {
  const stage = document.getElementById('stage');
  const track = document.getElementById('track');
  const progress = document.getElementById('progress');
  const next = document.getElementById('next');
  const hint = document.getElementById('hint');
  let total = 0;
  let slides = [];
  let fills = [];

  function load(facts) {
    total = facts.length;
    track.replaceChildren(...facts.map((f, i) => slideFor(f, i, total)));
    slides = [...track.children];
    progress.replaceChildren(...facts.map(() => {
      const seg = el('span', 'seg');
      seg.append(el('span', 'seg-fill'));
      return seg;
    }));
    fills = [...progress.querySelectorAll('.seg-fill')];
  }

  let width = stage.clientWidth || 1;
  let index = 0;

  const x = spring(0, render);

  function render(value) {
    track.style.setProperty('transform', `translate3d(${value}px,0,0)`);
    const pos = -value / width;
    fills.forEach((f, i) => f.style.setProperty('transform', `scaleX(${Math.min(1, Math.max(0, pos - i + 1))})`));
    // Slides that are leaving recede a little, so the one arriving reads as in front.
    slides.forEach((s, i) => {
      const d = Math.min(1, Math.abs(pos - i));
      s.style.setProperty('opacity', String(1 - d * 0.65));
    });
  }

  function settle(i, velocity = 0) {
    const prev = index;
    index = Math.max(0, Math.min(total - 1, i));
    const flicked = Math.abs(velocity) > 400;
    x.to(-index * width, { velocity, damping: flicked ? 0.86 : 1, response: 0.38 });
    if (prev !== index) {
      slides.forEach((s, k) => s.setAttribute('aria-hidden', String(k !== index)));
      announce();
      if (reducedMotion.matches) {
        slides[index].classList.remove('fade-in');
        void slides[index].offsetWidth; // restart the cross-fade
        slides[index].classList.add('fade-in');
      }
    }
    updateFooter();
  }

  // Screen readers hear the new fact; the slides themselves only flip aria-hidden.
  function announce() {
    const s = slides[index];
    document.getElementById('reveal-live').textContent =
      [...s.querySelectorAll('.kicker, .big, .row-fact, .line')].map((n) => n.textContent).join('. ');
  }

  function updateFooter() {
    const last = index === total - 1;
    next.textContent = last ? 'Make our poster' : 'Next';
    hint.classList.toggle('is-gone', index > 0);
  }

  function go(delta) {
    if (index + delta >= total) {
      onDone();
      return;
    }
    settle(index + delta);
  }

  // ---- pointer: track 1:1 after 10 px of horizontal intent, then throw.
  const tracker = velocityTracker();
  let pointer = null;

  stage.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    x.stop(); // grab it where it is, even mid-flight
    pointer = { id: e.pointerId, sx: e.clientX, sy: e.clientY, base: x.value, mode: 'pending' };
    tracker.reset();
    tracker.add(e.clientX, e.timeStamp);
    stage.classList.add('is-pressed');
  });

  stage.addEventListener('pointermove', (e) => {
    if (!pointer || e.pointerId !== pointer.id) return;
    const dx = e.clientX - pointer.sx;
    const dy = e.clientY - pointer.sy;
    if (pointer.mode === 'pending') {
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
      pointer.mode = Math.abs(dx) > Math.abs(dy) ? 'drag' : 'none';
      if (pointer.mode === 'drag') stage.setPointerCapture(e.pointerId);
    }
    if (pointer.mode !== 'drag') return;
    tracker.add(e.clientX, e.timeStamp);
    const min = -(total - 1) * width;
    let v = pointer.base + dx;
    if (v > 0) v = rubberband(v, width);
    if (v < min) v = min + rubberband(v - min, width);
    x.set(v);
  });

  function release(e) {
    if (!pointer || e.pointerId !== pointer.id) return;
    stage.classList.remove('is-pressed');
    const mode = pointer.mode;
    const base = pointer.base;
    pointer = null;
    if (mode === 'drag') {
      const v = tracker.velocity(e.timeStamp);
      const from = Math.round(-base / width);
      const projected = x.value + project(v, 0.99);
      let target = Math.round(-projected / width);
      target = Math.max(from - 1, Math.min(from + 1, target));
      settle(target, v);
    } else if (mode === 'pending' && e.type === 'pointerup') {
      // A tap: left third goes back, anywhere else goes on, like stories.
      const r = stage.getBoundingClientRect();
      const back = e.clientX - r.left < r.width / 3;
      if (back) settle(index - 1);
      else go(1);
    } else {
      settle(index);
    }
  }
  stage.addEventListener('pointerup', release);
  stage.addEventListener('pointercancel', release);

  next.addEventListener('click', () => go(1));

  function onKey(e) {
    if (e.target.closest && e.target.closest('input, textarea')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); settle(index - 1); }
  }

  function onResize() {
    width = stage.clientWidth || 1;
    x.set(-index * width);
  }

  return {
    load,
    start(at = 0) {
      width = stage.clientWidth || 1;
      index = at;
      slides.forEach((s, k) => s.setAttribute('aria-hidden', String(k !== index)));
      x.set(-index * width);
      updateFooter();
      document.addEventListener('keydown', onKey);
      window.addEventListener('resize', onResize);
    },
    stop() {
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('resize', onResize);
    },
    get index() { return index; },
  };
}
