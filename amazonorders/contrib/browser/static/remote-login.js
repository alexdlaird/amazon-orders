// The page through which a person signs in to Amazon from their own browser, while the browser doing the sign-in runs
// headless where amazon-orders runs: it shows that browser's page as it's drawn, and passes clicks, taps, scrolling,
// typing and pastes on to it. See amazonorders/contrib/browser/remote.py.
"use strict";

(() => {
  const base = location.pathname.replace(/\/+$/, "");
  const site = document.body.dataset.site;
  const statusText = document.getElementById("status");
  const keyboardButton = document.getElementById("keyboard");
  const pasteButton = document.getElementById("paste");
  const screenArea = document.getElementById("screen");
  const canvas = document.getElementById("canvas");
  const context = canvas.getContext("2d");
  const input = document.getElementById("input");

  const MESSAGES = {
    starting: "Opening Amazon's sign-in page…",
    signing_in: `Sign in to ${site} below. What you type goes to Amazon's page.`,
    verifying: "Checking the sign-in with Amazon…",
    signed_in: `You're signed in to ${site}. You can close this page.`,
    failed: "The sign-in didn't complete. Start a new sign-in to try again.",
    timed_out: "This sign-in ran out of time. Start a new sign-in to try again.",
    claimed: "This sign-in is open in another browser. Use that one, or start a new sign-in.",
    gone: "This sign-in link isn't valid anymore. Start a new sign-in for a new link.",
    offline: "Reconnecting…",
    paste_failed: "This browser didn't let the page read the clipboard. Type it instead.",
  };
  const FINAL_STATES = new Set(["signed_in", "failed", "timed_out", "claimed", "gone"]);
  const SPECIAL_KEYS = new Set(["Enter", "Tab", "Backspace", "Delete", "Escape", "ArrowLeft", "ArrowRight", "ArrowUp",
    "ArrowDown", "Home", "End", "PageUp", "PageDown"]);
  const MOUSE_BUTTONS = ["left", "middle", "right"];
  const MAX_TEXT_LENGTH = 1000;
  const MAX_EVENTS_PER_REQUEST = 100;
  const TAP_SLOP = 10;
  // What the hidden text box holds between keystrokes, so typing from a phone's keyboard (which sends no usable key
  // events) shows up as text added after it, and deleting as it getting shorter
  const SENTINEL = "_".repeat(16);

  let state = "starting";
  let ended = false;
  let seq = 0;
  let viewport = {width: 0, height: 0};
  let composing = false;
  let touch = null;
  let pending = [];
  let sending = false;
  let resizeTimer = null;
  let reportedSize = "";

  function setState(next) {
    if (ended || !MESSAGES[next]) {
      return;
    }
    state = next;
    statusText.textContent = MESSAGES[next];
    if (FINAL_STATES.has(next)) {
      ended = true;
      pending = [];
      document.body.classList.add("ended");
      keyboardButton.hidden = true;
      pasteButton.hidden = true;
      input.blur();
    }
  }

  function showOffline(offline) {
    if (!ended) {
      statusText.textContent = offline ? MESSAGES.offline : MESSAGES[state];
    }
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function request(path, options) {
    return fetch(`${base}/${path}`, {credentials: "same-origin", cache: "no-store", ...options});
  }

  function endOnRefusal(response) {
    if (response.status === 404) {
      setState("gone");
    } else if (response.status === 409) {
      setState("claimed");
    }
    return ended;
  }

  // Input

  function send(event) {
    if (ended) {
      return;
    }
    const last = pending[pending.length - 1];
    if (event.t === "move" && last && last.t === "move") {
      pending[pending.length - 1] = event;
    } else {
      pending.push(event);
    }
    flush();
  }

  async function flush() {
    if (sending || pending.length === 0) {
      return;
    }
    sending = true;
    const batch = pending.splice(0, MAX_EVENTS_PER_REQUEST);
    try {
      const response = await request("input", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(batch),
      });
      endOnRefusal(response);
    } catch (error) {
      // The frame requests show the connection is lost; what was typed meanwhile has to be typed again
    }
    sending = false;
    flush();
  }

  function sendText(text, kind) {
    text.split(/\r\n|\r|\n/).forEach((line, index) => {
      if (index > 0) {
        send({t: "key", key: "Enter", mods: []});
      }
      for (let start = 0; start < line.length; start += MAX_TEXT_LENGTH) {
        send({t: kind, text: line.slice(start, start + MAX_TEXT_LENGTH)});
      }
    });
  }

  function modifiers(event) {
    const mods = [];
    if (event.altKey && !event.getModifierState("AltGraph")) {
      mods.push("Alt");
    }
    if (event.ctrlKey && !event.getModifierState("AltGraph")) {
      mods.push("Control");
    }
    if (event.metaKey) {
      mods.push("Meta");
    }
    if (event.shiftKey) {
      mods.push("Shift");
    }
    return mods;
  }

  function resetInput() {
    input.value = SENTINEL;
    input.setSelectionRange(SENTINEL.length, SENTINEL.length);
  }

  function readInput() {
    const value = input.value;
    if (value === SENTINEL) {
      return;
    }
    let common = 0;
    while (common < value.length && common < SENTINEL.length && value[common] === SENTINEL[common]) {
      common++;
    }
    for (let removed = SENTINEL.length - common; removed > 0; removed--) {
      send({t: "key", key: "Backspace", mods: []});
    }
    const added = value.slice(common);
    sendText(added, Array.from(added).length === 1 ? "type" : "insert");
    resetInput();
  }

  function focusInput() {
    if (!ended && document.activeElement !== input) {
      input.focus({preventScroll: true});
    }
  }

  input.addEventListener("keydown", (event) => {
    if (event.isComposing || composing || event.keyCode === 229) {
      return;
    }
    const mods = modifiers(event);
    if (SPECIAL_KEYS.has(event.key)) {
      event.preventDefault();
      send({t: "key", key: event.key, mods});
    } else if (Array.from(event.key).length === 1 && (mods.includes("Control") || mods.includes("Meta"))) {
      // Ctrl+V or Cmd+V pastes from this computer's clipboard, through the paste event
      if (event.key.toLowerCase() !== "v" && /^[a-z0-9]$/i.test(event.key)) {
        event.preventDefault();
        send({t: "key", key: event.key.toLowerCase(), mods});
      }
    } else if (Array.from(event.key).length === 1) {
      event.preventDefault();
      send({t: "type", text: event.key});
    }
  });
  input.addEventListener("compositionstart", () => {
    composing = true;
  });
  input.addEventListener("compositionend", () => {
    composing = false;
    readInput();
  });
  input.addEventListener("input", () => {
    if (!composing) {
      readInput();
    }
  });
  input.addEventListener("paste", (event) => {
    event.preventDefault();
    const text = event.clipboardData ? event.clipboardData.getData("text/plain") : "";
    if (text) {
      sendText(text, "insert");
    }
  });

  function pagePoint(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: Math.round((event.clientX - rect.left) * viewport.width / rect.width * 10) / 10,
      y: Math.round((event.clientY - rect.top) * viewport.height / rect.height * 10) / 10,
    };
  }

  canvas.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    if (!viewport.width) {
      return;
    }
    if (composing) {
      // A phone's keyboard holds back a word until it's done with it: leaving the text box hands it over, so the word
      // reaches the page before the tap does
      input.blur();
    }
    if (event.pointerType === "mouse") {
      canvas.setPointerCapture(event.pointerId);
      send({t: "down", ...pagePoint(event), button: MOUSE_BUTTONS[event.button] || "left"});
      focusInput();
    } else if (!touch) {
      touch = {id: event.pointerId, x: event.clientX, y: event.clientY, start: pagePoint(event), scrolled: false};
    }
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!viewport.width) {
      return;
    }
    if (event.pointerType === "mouse") {
      send({t: "move", ...pagePoint(event)});
      return;
    }
    if (!touch || touch.id !== event.pointerId) {
      return;
    }
    const dx = event.clientX - touch.x;
    const dy = event.clientY - touch.y;
    if (!touch.scrolled && Math.hypot(dx, dy) < TAP_SLOP) {
      return;
    }
    // Dragging a finger scrolls the page, the other way to the finger
    const rect = canvas.getBoundingClientRect();
    touch.scrolled = true;
    touch.x = event.clientX;
    touch.y = event.clientY;
    send({t: "wheel", ...pagePoint(event), dx: -dx * viewport.width / rect.width, dy: -dy * viewport.height / rect.height});
  });
  canvas.addEventListener("pointerup", (event) => {
    if (!viewport.width) {
      return;
    }
    if (event.pointerType === "mouse") {
      send({t: "up", ...pagePoint(event), button: MOUSE_BUTTONS[event.button] || "left"});
    } else if (touch && touch.id === event.pointerId) {
      if (!touch.scrolled) {
        send({t: "down", ...touch.start, button: "left"});
        send({t: "up", ...touch.start, button: "left"});
        // Inside the tap, so a phone opens its keyboard for the field tapped
        focusInput();
      }
      touch = null;
    }
  });
  canvas.addEventListener("pointercancel", () => {
    touch = null;
  });
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    if (!viewport.width) {
      return;
    }
    const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.height : 1;
    send({t: "wheel", ...pagePoint(event), dx: event.deltaX * unit, dy: event.deltaY * unit});
  }, {passive: false});
  canvas.addEventListener("contextmenu", (event) => event.preventDefault());

  keyboardButton.addEventListener("click", focusInput);
  // Phones have no paste key, and the text box that takes the typing can't be long-pressed, since it's out of sight
  pasteButton.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        sendText(text, "insert");
      }
    } catch (error) {
      statusText.textContent = MESSAGES.paste_failed;
      setTimeout(() => showOffline(false), 4000);
    }
    focusInput();
  });

  // Size

  function layout() {
    if (!viewport.width || !viewport.height) {
      return;
    }
    const scale = Math.min(1, screenArea.clientWidth / viewport.width, screenArea.clientHeight / viewport.height);
    canvas.style.width = `${viewport.width * scale}px`;
    canvas.style.height = `${viewport.height * scale}px`;
  }

  function reportSize() {
    // A phone's keyboard covers the page without resizing it in some browsers; the visual viewport says what's left
    if (window.visualViewport) {
      document.body.style.height = `${window.visualViewport.height}px`;
    }
    const width = Math.round(screenArea.clientWidth);
    const height = Math.round(screenArea.clientHeight);
    const density = Math.min(window.devicePixelRatio || 1, 4);
    const size = `${width}x${height}@${density}`;
    if (width > 0 && height > 0 && size !== reportedSize) {
      reportedSize = size;
      send({t: "size", w: width, h: height, dpr: density});
    }
    layout();
  }

  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(reportSize, 200);
  }

  window.addEventListener("resize", onResize);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", onResize);
  }
  // The area left for the page also changes without the window resizing, e.g. when the status above it wraps
  if (window.ResizeObserver) {
    new ResizeObserver(onResize).observe(screenArea);
  }

  // Frames

  async function draw(blob) {
    let image;
    if (window.createImageBitmap) {
      image = await createImageBitmap(blob);
    } else {
      image = new Image();
      const url = URL.createObjectURL(blob);
      image.src = url;
      await image.decode();
      URL.revokeObjectURL(url);
    }
    if (canvas.width !== image.width || canvas.height !== image.height) {
      canvas.width = image.width;
      canvas.height = image.height;
    }
    context.drawImage(image, 0, 0);
    if (image.close) {
      image.close();
    }
  }

  async function pollOnce() {
    const response = await request(`frame?after=${seq}&state=${encodeURIComponent(state)}`);
    if (endOnRefusal(response)) {
      return;
    }
    if (response.status === 200 && response.headers.get("Content-Type") === "image/jpeg") {
      const frameSeq = Number(response.headers.get("X-Frame-Seq"));
      const frameViewport = {
        width: Number(response.headers.get("X-Viewport-Width")),
        height: Number(response.headers.get("X-Viewport-Height")),
      };
      await draw(await response.blob());
      seq = frameSeq;
      viewport = frameViewport;
      layout();
    } else if (response.status === 200) {
      setState((await response.json()).state);
      return;
    } else if (!response.ok) {
      await sleep(1000);
    }
    setState(response.headers.get("X-Sign-In-State") || state);
  }

  async function poll() {
    let failures = 0;
    while (!ended) {
      try {
        await pollOnce();
        failures = 0;
        showOffline(false);
      } catch (error) {
        // A lost connection, or a frame that didn't arrive whole: wait a little, then ask again
        failures++;
        showOffline(true);
        await sleep(Math.min(1000 * failures, 5000));
      }
    }
  }

  function start() {
    keyboardButton.hidden = !window.matchMedia("(pointer: coarse)").matches;
    pasteButton.hidden = !(navigator.clipboard && navigator.clipboard.readText);
    statusText.textContent = MESSAGES.starting;
    resetInput();
    reportSize();
    focusInput();
    poll();
  }

  start();
})();
