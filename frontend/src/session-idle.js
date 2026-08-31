export const SESSION_IDLE_MS = 10 * 60 * 1000;

export function createSessionIdleDeadline({
  idleMs = SESSION_IDLE_MS,
  now = Date.now,
  setTimer = globalThis.setTimeout,
  clearTimer = globalThis.clearTimeout,
  onExpire,
} = {}) {
  if (typeof onExpire !== "function") {
    throw new TypeError("onExpire is required");
  }

  let active = true;
  let timer;
  let deadline = now() + idleMs;

  const stop = () => {
    if (!active) return;
    active = false;
    clearTimer(timer);
  };
  const expire = () => {
    if (!active) return;
    stop();
    onExpire();
  };
  const schedule = () => {
    if (!active) return;
    clearTimer(timer);
    const remaining = deadline - now();
    if (remaining <= 0) {
      expire();
      return;
    }
    timer = setTimer(check, remaining);
  };
  function check() {
    if (now() >= deadline) {
      expire();
      return;
    }
    schedule();
  }
  const recordActivity = () => {
    if (!active) return false;
    const current = now();
    if (current >= deadline) {
      expire();
      return false;
    }
    deadline = current + idleMs;
    schedule();
    return true;
  };

  schedule();
  return { recordActivity, stop };
}
