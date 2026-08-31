import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createSessionIdleDeadline, SESSION_IDLE_MS } from "../src/session-idle.js";

const main = readFileSync(new URL("../src/main.jsx", import.meta.url), "utf8");
const idleSource = readFileSync(new URL("../src/session-idle.js", import.meta.url), "utf8");

function fakeClock() {
  let current = 0;
  let nextTimer = 0;
  const timers = new Map();
  const runDue = () => {
    let due;
    do {
      due = [...timers.entries()]
        .filter(([, timer]) => timer.at <= current)
        .sort((left, right) => left[1].at - right[1].at)[0];
      if (due) {
        timers.delete(due[0]);
        due[1].callback();
      }
    } while (due);
  };
  return {
    now: () => current,
    setTimer: (callback, delay) => {
      const id = ++nextTimer;
      timers.set(id, { callback, at: current + delay });
      return id;
    },
    clearTimer: (id) => timers.delete(id),
    advance: (milliseconds, { runTimers = true } = {}) => {
      current += milliseconds;
      if (runTimers) runDue();
    },
  };
}

test("the browser session expires after ten minutes without human activity", () => {
  const idleRuntime = main.slice(
    main.indexOf("let lastSync = 0"),
    main.indexOf("const warnBeforeUnload"),
  );

  assert.equal(SESSION_IDLE_MS, 600_000);
  assert.match(idleSource, /const SESSION_IDLE_MS = 10 \* 60 \* 1000;/);
  assert.match(idleRuntime, /createSessionIdleDeadline\(\{ onExpire: expireSession \}\)/);
  assert.doesNotMatch(idleRuntime, /window\.setInterval\(/);

  const clock = fakeClock();
  let expirations = 0;
  const deadline = createSessionIdleDeadline({
    ...clock,
    onExpire: () => { expirations += 1; },
  });
  clock.advance(SESSION_IDLE_MS - 1);
  assert.equal(expirations, 0);
  clock.advance(1);
  assert.equal(expirations, 1);
  assert.equal(deadline.recordActivity(), false);
});

test("an expired session clears its route and returns to Login", () => {
  const expiration = main.slice(
    main.indexOf("const expireSession = () =>"),
    main.indexOf("const scheduleExpiration = () =>"),
  );

  assert.match(expiration, /localStorage\.removeItem\("access_token"\)/);
  assert.match(expiration, /window\.history\.replaceState\(/);
  assert.match(expiration, /setUser\(null\)/);
  assert.match(main, /if \(!user\) return <Login onLogin=\{setUser\} \/>/);
});

test("returning to a throttled tab cannot revive an already idle session", () => {
  const clock = fakeClock();
  let expirations = 0;
  const deadline = createSessionIdleDeadline({
    ...clock,
    onExpire: () => { expirations += 1; },
  });

  clock.advance(SESSION_IDLE_MS + 1, { runTimers: false });
  assert.equal(deadline.recordActivity(), false);
  assert.equal(expirations, 1);
  assert.match(main, /if \(!idleDeadline\.recordActivity\(\)\) return;/);
  assert.match(main, /if \(document\.visibilityState === "visible"\) registerActivity\(\)/);
});

test("human activity before the limit moves the deadline", () => {
  const clock = fakeClock();
  let expirations = 0;
  const deadline = createSessionIdleDeadline({
    ...clock,
    onExpire: () => { expirations += 1; },
  });

  clock.advance(5 * 60 * 1000);
  assert.equal(deadline.recordActivity(), true);
  clock.advance(5 * 60 * 1000);
  assert.equal(expirations, 0);
  clock.advance(5 * 60 * 1000);
  assert.equal(expirations, 1);
});
