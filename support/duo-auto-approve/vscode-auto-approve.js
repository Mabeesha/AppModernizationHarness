#!/usr/bin/env node
// vscode-auto-approve.js - runs on its own, outside VS Code. Whenever VS Code is open (started
// with the debugging port, see below), it finds the GitLab Duo chat panel and clicks "Approve"
// on tool calls, except commands that match the BLOCK list. Close VS Code, reopen it, reload
// the window: the script reconnects by itself.
//
// No npm packages needed (Node 22 or later). On older Node: npm i ws
//
// 1. Make VS Code always open with the debugging port. Edit the shortcut you start it from
//    (Start menu / taskbar: right-click > Properties) and add to the end of "Target":
//        --remote-debugging-port=9333
//    The port only works if VS Code was fully closed first; a new window of an already
//    running VS Code keeps whatever the first one started with.
// 2. Run this script (and leave it running):
//        node C:\tools\duo-aa\vscode-auto-approve.js
//    To start it at login: put a shortcut to that command in shell:startup.
//
// In the script's window:  p = pause/resume,  Ctrl+C = stop.
// Log: %TEMP%\vscode-auto-approve.log
//
// Settings (environment variables):
//   VSAA_PORT=9333                  must match the VS Code shortcut
//   VSAA_WEBVIEW=gitlab             text in the Duo panel's webview address (extension id)
//   VSAA_BUTTON=Approve             the button text to click
//   VSAA_FRAME=agentic|duo          name or address of the frames holding the Duo chat
//   VSAA_EVERY_MS=1500              how often to check

const fs = require('fs');
const os = require('os');
const path = require('path');
const WS = globalThis.WebSocket || require('ws');

const PORT = Number(process.env.VSAA_PORT || 9333);
const WEBVIEW = new RegExp(process.env.VSAA_WEBVIEW || 'gitlab', 'i');
const BUTTON = process.env.VSAA_BUTTON || 'Approve';
const EVERY_MS = Number(process.env.VSAA_EVERY_MS || 1500);
const SCHEME = process.env.VSAA_SCHEME || 'vscode-webview://';   // only changed for testing
// The Duo chat itself is served by the GitLab extension from a local address
// (http://127.0.0.1:<port>) in frames named "agentic-tabs" / "iframe-chat". A frame whose
// name or address matches this is searched too.
const DUO_FRAME = new RegExp(process.env.VSAA_FRAME || 'agentic|duo', 'i');

// Never auto-approved; you approve or deny these yourself.
const BLOCK = [
  'Remove-Item', '\\bri\\b', '\\brm\\b', '\\brmdir\\b', '\\brd\\b', '\\bdel\\b', '\\berase\\b',
  'Format-', 'Stop-Computer', 'Restart-Computer', 'Clear-Content',
  'git\\b[^\\n]*\\bpush\\b', 'git\\b[^\\n]*\\breset\\s+--hard', 'git\\b[^\\n]*\\bclean\\b',
  'git\\b[^\\n]*\\bcheckout\\s+--\\s', 'git\\b[^\\n]*\\bbranch\\s+-D\\b',
].join('|');

const LOG = path.join(os.tmpdir(), 'vscode-auto-approve.log');
function log(msg) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
  console.log(line);
  try { fs.appendFileSync(LOG, line + '\n'); } catch {}
}

// ---- runs inside the Duo webview: same idea as the DevTools snippet ------------------------
// Looks through the webview and any same-origin frames in it (the chat is in "iframe-chat").
const PAGE_FN = `(() => {
  const BLOCK = new RegExp(${JSON.stringify(BLOCK)}, 'i');
  const docs = [];
  (function walk(d) {
    docs.push(d);
    for (const f of d.querySelectorAll('iframe')) {
      try { if (f.contentDocument) walk(f.contentDocument); } catch (e) {}
    }
  })(document);
  for (const d of docs) {
    // Never click the same button twice: after a click Duo's button keeps spinning, still
    // "enabled", and clicking it again can confuse it.
    const btn = [...d.querySelectorAll('button')]
      .find(b => b.innerText.trim() === ${JSON.stringify(BUTTON)} && !b.disabled && !b.dataset.vsaaClicked);
    if (!btn) continue;
    const card = btn.closest('div:has(pre), div:has(code)') || btn.parentElement;
    const cmd = card ? card.innerText.slice(0, 1000) : '';
    const hit = cmd.match(BLOCK);
    if (hit) {
      // Remember the skip, and never click it on a later check either.
      if (window.__vsaaSkip === cmd) return null;
      window.__vsaaSkip = cmd;
      return { action: 'skipped', match: hit[0], cmd };
    }
    btn.dataset.vsaaClicked = '1';
    btn.click();
    return { action: 'approved', cmd };
  }
  return null;
})()`;

// ---- a minimal Chrome DevTools Protocol client ------------------------------------------------
class CDP {
  constructor(url) { this.url = url; this.id = 0; this.waiting = new Map(); this.onEvent = () => {}; }
  open() {
    return new Promise((resolve, reject) => {
      this.ws = new WS(this.url);
      const on = (ev, fn) => this.ws.addEventListener ? this.ws.addEventListener(ev, fn) : this.ws.on(ev, fn);
      on('open', () => resolve());
      on('error', (e) => reject(e));
      on('close', () => {
        this.closed = true;
        for (const { reject: r } of this.waiting.values()) r(new Error('closed'));
        this.waiting.clear();
      });
      on('message', (m) => {
        const msg = JSON.parse(m.data ?? m);
        if (msg.id && this.waiting.has(msg.id)) {
          const { resolve: ok, reject: bad } = this.waiting.get(msg.id);
          this.waiting.delete(msg.id);
          msg.error ? bad(new Error(msg.error.message)) : ok(msg.result);
        } else if (msg.method) this.onEvent(msg);
      });
    });
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    return new Promise((resolve, reject) => {
      this.waiting.set(id, { resolve, reject });
      setTimeout(() => { if (this.waiting.delete(id)) reject(new Error(`timeout: ${method}`)); }, 10_000);
    });
  }
  close() { try { this.ws.close(); } catch {} }
}

// ---- main loop ------------------------------------------------------------------------------
// VS Code may run a webview as its own process (a separate "iframe" target) or inside the main
// window's process (a frame of the "page" target). To cover both, the script attaches to every
// page and webview target, lists each one's frames, and runs PAGE_FN in the JavaScript context
// of every frame whose address is a GitLab webview.
let cdp = null;
const sessions = new Map();        // targetId -> sessionId
const contexts = new Map();        // sessionId -> Map(frameId -> contextId)
let paused = false;
let waitingNoted = false;
let lastFound = -1;
let noneSince = 0;
let hinted = false;

async function connect() {
  const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
  const { webSocketDebuggerUrl } = await res.json();
  const c = new CDP(webSocketDebuggerUrl);
  await c.open();
  c.onEvent = (msg) => {
    const sid = msg.sessionId;
    if (msg.method === 'Target.detachedFromTarget') {
      for (const [t, s] of sessions) if (s === msg.params.sessionId) sessions.delete(t);
      contexts.delete(msg.params.sessionId);
    } else if (msg.method === 'Runtime.executionContextCreated' && sid) {
      const ctx = msg.params.context;
      const frameId = ctx.auxData && ctx.auxData.frameId;
      if (frameId && ctx.auxData.isDefault) {
        if (!contexts.has(sid)) contexts.set(sid, new Map());
        contexts.get(sid).set(frameId, ctx.id);
      }
    } else if (msg.method === 'Runtime.executionContextDestroyed' && sid) {
      const m = contexts.get(sid);
      if (m) for (const [f, id] of m) if (id === msg.params.executionContextId) m.delete(f);
    } else if (msg.method === 'Runtime.executionContextsCleared' && sid) {
      contexts.set(sid, new Map());
    }
  };
  sessions.clear(); contexts.clear();
  cdp = c;
  waitingNoted = false; lastFound = -1; noneSince = Date.now(); hinted = false;
  log(`connected to VS Code on port ${PORT}`);
}

async function attach(targetId) {
  let sessionId = sessions.get(targetId);
  if (sessionId) return sessionId;
  ({ sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true }));
  sessions.set(targetId, sessionId);
  contexts.set(sessionId, new Map());
  await cdp.send('Runtime.enable', {}, sessionId);   // reports every frame's context to us
  return sessionId;
}

function flatten(tree, out = []) {
  out.push(tree.frame);
  for (const c of tree.childFrames || []) flatten(c, out);
  return out;
}

async function tick() {
  if (!cdp || cdp.closed) {
    if (cdp) { log('VS Code closed - waiting for it to open again'); cdp = null; }
    try { await connect(); }
    catch {
      if (!waitingNoted) {
        log(`waiting for VS Code (started with --remote-debugging-port=${PORT})...`);
        waitingNoted = true;
      }
      return;
    }
  }
  if (paused) return;

  const { targetInfos } = await cdp.send('Target.getTargets');
  // Main windows, and frames VS Code runs in a process of their own.
  const targets = targetInfos.filter((t) => ['page', 'iframe', 'webview'].includes(t.type));

  let found = 0;
  const seenWebviews = new Set();
  for (const t of targets) {
    let sessionId;
    try { sessionId = await attach(t.targetId); } catch { continue; }
    let frames;
    try { frames = flatten((await cdp.send('Page.getFrameTree', {}, sessionId)).frameTree); }
    catch { sessions.delete(t.targetId); continue; }
    const ctx = contexts.get(sessionId) || new Map();
    const byId = new Map(frames.map((f) => [f.id, f]));
    const origin = (u) => (u.match(/^[a-z-]+:\/\/[^/?#]*/i) || [u])[0];
    const isDuo = (f) => (f.url.startsWith(SCHEME) && WEBVIEW.test(f.url)) ||
      (/^https?:\/\/(127(\.\d+){3}|localhost)[:/]/i.test(f.url) && DUO_FRAME.test(`${f.name || ''} ${f.url}`));
    const chosen = new Set();
    for (const f of frames) {
      if (f.url.startsWith(SCHEME)) {
        seenWebviews.add(f.url.split('?')[0] + ' ' + (f.url.match(/extensionId=[^&]+/) || [''])[0]);
      }
      if (!isDuo(f)) continue;
      // PAGE_FN walks into child frames of the same origin itself, so skip those.
      const parent = f.parentId && byId.get(f.parentId);
      if (parent && chosen.has(parent.id) && origin(parent.url) === origin(f.url)) { chosen.add(f.id); continue; }
      chosen.add(f.id);
      const contextId = ctx.get(f.id);
      if (!contextId) continue;         // this frame runs in another target; handled there
      found++;
      let r;
      try {
        r = await cdp.send('Runtime.evaluate', { expression: PAGE_FN, returnByValue: true, contextId }, sessionId);
      } catch { continue; }
      const v = r && r.result && r.result.value;
      if (!v) continue;
      const first = v.cmd.split('\n').map((x) => x.trim()).filter(Boolean).slice(0, 3).join(' | ');
      if (v.action === 'approved') log(`APPROVED: ${first}`);
      else { log(`SKIPPED (matched "${v.match}") - approve or deny it yourself: ${first}`); process.stdout.write('\x07'); }
    }
  }

  if (found !== lastFound) {
    log(found ? `watching ${found} GitLab Duo frame(s)` : 'no GitLab Duo panel found yet - open the Duo chat');
    lastFound = found;
    if (found) hinted = false; else noneSince = Date.now();
  }
  if (!found && !hinted && Date.now() - noneSince > 10_000) {
    hinted = true;
    log(seenWebviews.size
      ? `webviews seen (set VSAA_WEBVIEW to text from the Duo one):\n  ${[...seenWebviews].join('\n  ')}`
      : 'no webviews seen at all - is the Duo chat panel open?');
  }
}

async function loop() {
  try { await tick(); } catch (e) { if (cdp && !cdp.closed) log(`error: ${e.message}`); }
  setTimeout(loop, EVERY_MS);
}

if (process.stdin.isTTY) {
  process.stdin.setRawMode(true);
  process.stdin.on('data', (b) => {
    const k = b.toString();
    if (k === '\x03') { log('stopped'); process.exit(0); }
    if (k.toLowerCase() === 'p') { paused = !paused; log(paused ? 'PAUSED (p to resume)' : 'RESUMED'); }
  });
}
log(`vscode-auto-approve running. p = pause/resume, Ctrl+C = stop. Log: ${LOG}`);
loop();
