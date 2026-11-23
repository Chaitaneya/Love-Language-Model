// The receipts sheet. Rises from the bottom, leaves the same way, and can be dragged
// down from its header. A flick closes it even from near the top; a slow drag has
// to pass halfway.

import { spring, velocityTracker, project, rubberband } from './spring.js';

export function createSheet({ onOpen } = {}) {
  const sheet = document.getElementById('sheet');
  const scrim = document.getElementById('scrim');
  const grab = document.getElementById('sheet-grab');
  const title = document.getElementById('sheet-title');
  const app = document.getElementById('app');
  let height = 0;
  let open = false;
  let returnFocus = null;

  const y = spring(0, (v) => {
    sheet.style.setProperty('transform', `translate3d(0,${v}px,0)`);
    scrim.style.setProperty('opacity', String(Math.max(0, Math.min(1, 1 - v / (height || 1)))));
  });

  function measure() {
    height = sheet.getBoundingClientRect().height;
  }

  function show(trigger) {
    if (open) return;
    open = true;
    returnFocus = trigger || document.activeElement;
    sheet.hidden = false;
    scrim.hidden = false;
    measure();
    if (!y.moving) y.set(height);
    app.inert = true;
    if (onOpen) onOpen();
    y.to(0, { damping: 1, response: 0.38 });
    title.focus({ preventScroll: true });
    document.addEventListener('keydown', onKey);
  }

  function hide(velocity = 0) {
    if (!open) return;
    open = false;
    app.inert = false;
    document.removeEventListener('keydown', onKey);
    y.to(height, {
      velocity,
      damping: 1,
      response: 0.34,
      onRest: () => {
        if (!open) {
          sheet.hidden = true;
          scrim.hidden = true;
        }
      },
    });
    if (returnFocus) returnFocus.focus({ preventScroll: true });
  }

  function onKey(e) {
    if (e.key === 'Escape') hide();
  }

  // Drag from the header, 1:1, rubber-banding if pulled above its resting place.
  const tracker = velocityTracker();
  let drag = null;
  grab.addEventListener('pointerdown', (e) => {
    if (e.button !== 0 || e.target.closest('button')) return;
    y.stop();
    grab.setPointerCapture(e.pointerId);
    drag = { id: e.pointerId, start: e.clientY, base: y.value };
    tracker.reset();
    tracker.add(e.clientY, e.timeStamp);
    sheet.classList.add('is-dragging');
  });
  grab.addEventListener('pointermove', (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    tracker.add(e.clientY, e.timeStamp);
    let v = drag.base + (e.clientY - drag.start);
    if (v < 0) v = rubberband(v, height);
    y.set(v);
  });
  function end(e) {
    if (!drag || e.pointerId !== drag.id) return;
    drag = null;
    sheet.classList.remove('is-dragging');
    const v = tracker.velocity(e.timeStamp);
    const landing = y.value + project(v);
    // Decide by where the throw would land, then hand the finger's speed to the spring.
    if (landing > height * 0.5) {
      hide(v);
    } else {
      y.to(0, { velocity: v, damping: Math.abs(v) > 300 ? 0.8 : 1, response: 0.3 });
    }
  }
  grab.addEventListener('pointerup', end);
  grab.addEventListener('pointercancel', end);
  scrim.addEventListener('click', () => hide());
  document.getElementById('close-receipts').addEventListener('click', () => hide());
  window.addEventListener('resize', () => {
    if (!open) return;
    measure();
  });

  return { show, hide, get open() { return open; } };
}
