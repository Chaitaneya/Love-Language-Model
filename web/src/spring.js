// Springs and gesture helpers. Plain functions, no dependencies.
//
// A spring is described the way Apple describes it: a damping ratio (1 = no overshoot)
// and a response in seconds (how quickly it gets there). It always animates from its
// current value and velocity, so calling to() mid-flight re-targets without a jump.

export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

export function spring(initial, onUpdate) {
  let value = initial;
  let velocity = 0;
  let target = initial;
  let stiffness = 0;
  let friction = 0;
  let raf = 0;
  let last = 0;
  let onRest = null;

  function configure(damping, response) {
    stiffness = (2 * Math.PI / response) ** 2;
    friction = (4 * Math.PI * damping) / response;
  }
  configure(1, 0.4);

  function frame(now) {
    // Follow real time even when frames drop (a busy or throttled page), so a 0.4 s spring still takes
    // about 0.4 s instead of running in slow motion. Small fixed sub-steps keep the integration stable.
    const dt = Math.min((now - last) / 1000, 0.25);
    last = now;
    const steps = Math.max(1, Math.ceil(dt / (1 / 240)));
    const h = dt / steps;
    for (let i = 0; i < steps; i++) {
      const accel = -stiffness * (value - target) - friction * velocity;
      velocity += accel * h;
      value += velocity * h;
    }
    if (Math.abs(velocity) < 2 && Math.abs(value - target) < 0.3) {
      value = target;
      velocity = 0;
      raf = 0;
      onUpdate(value);
      if (onRest) onRest();
      return;
    }
    onUpdate(value);
    raf = requestAnimationFrame(frame);
  }

  return {
    get value() { return value; },
    get target() { return target; },
    get moving() { return raf !== 0; },
    // Move toward t. velocity is in units per second (px/s for positions).
    to(t, opts = {}) {
      target = t;
      onRest = opts.onRest || null;
      if (typeof opts.velocity === 'number') velocity = opts.velocity;
      configure(opts.damping ?? 1, opts.response ?? 0.4);
      if (reducedMotion.matches) {
        this.set(t);
        if (onRest) onRest();
        return;
      }
      if (!raf) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    },
    // Jump with no animation (used while a finger is holding the element).
    set(v) {
      cancelAnimationFrame(raf);
      raf = 0;
      value = v;
      target = v;
      velocity = 0;
      onUpdate(value);
    },
    // Freeze at the presentation value so a finger can take over.
    stop() {
      cancelAnimationFrame(raf);
      raf = 0;
      velocity = 0;
      target = value;
    },
  };
}

// Recent pointer samples, so we know the finger's speed when it lets go.
export function velocityTracker() {
  let samples = [];
  return {
    reset() { samples = []; },
    add(pos, time) {
      samples.push({ pos, time });
      while (samples.length > 2 && time - samples[0].time > 100) samples.shift();
    },
    // Pass the release time: a finger that stopped before letting go has no speed.
    velocity(now = Infinity) {
      if (samples.length < 2) return 0;
      const a = samples[0];
      const b = samples[samples.length - 1];
      if (now - b.time > 60) return 0;
      const dt = b.time - a.time;
      return dt > 0 ? ((b.pos - a.pos) / dt) * 1000 : 0;
    },
  };
}

// Where a flick would come to rest (Apple's sample code, exponential deceleration).
export function project(velocity, decelerationRate = 0.998) {
  return ((velocity / 1000) * decelerationRate) / (1 - decelerationRate);
}

// Resist progressively past a boundary instead of stopping dead.
export function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
