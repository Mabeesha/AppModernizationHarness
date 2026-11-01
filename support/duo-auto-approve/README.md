# Duo auto-approve helpers

Helpers for **the developer running the harness on GitLab Duo**, not part of the harness itself.
The installers do not copy this folder into a target project, and no stage tells an agent to use it.

GitLab Duo in VS Code asks you to approve every tool call. On a long Stage 4 run that means
sitting at the screen clicking **Approve**. `vscode-auto-approve.js` clicks it for you, except
for commands on a blocked list, which it leaves for you to approve or deny.

## vscode-auto-approve.js

Runs in its own terminal window, outside VS Code. While VS Code is open, it finds the GitLab Duo
chat panel and approves tool calls. Close VS Code, reopen it or reload the window, and it
reconnects by itself.

### Setup (once)

1. **Node 22 or later.** No `npm install` is needed. On older Node, run `npm i ws` in this folder.
2. **Start VS Code with a debugging port.** Right-click the shortcut you start VS Code from
   (Start menu or taskbar) > **Properties**, and add this to the end of **Target**:

   ```
   --remote-debugging-port=9333
   ```

   Close every VS Code window first. A window opened while VS Code is already running keeps
   whatever the first one started with.

### Run

```powershell
node support\duo-auto-approve\vscode-auto-approve.js
```

Leave it running. In its window: `p` pauses or resumes, `r` refreshes the Duo chat view now,
`Ctrl+C` stops. Every approval and skip
is shown there and written to `%TEMP%\vscode-auto-approve.log`.

To start it at login: `Win+R` > `shell:startup`, and put a shortcut to that command in the
folder that opens.

### When the chat view gets stuck

Sometimes the chat stops updating, often at an approval, while the agent has moved on.
Switching to another session and back, or reloading VS Code, shows the real state. The script
does the same thing by reloading **only the Duo chat frame** (the page the GitLab extension
serves from `127.0.0.1`). VS Code, the editor and the terminals are not touched, and the agent's
run is not stopped: the chat screen is only a view of it.

It refreshes when all of these are true:

- Duo shows it is working ("GitLab Duo is working on your request. Please wait.");
- nothing in the chat has changed for `VSAA_STUCK_MINUTES` (default 3);
- the chat box is empty, so nothing you are typing is lost;
- no blocked command is waiting for you to approve or deny.

After a refresh, an approval that is still pending shows a fresh **Approve** button, and the
script approves it, which is the same as doing it by hand after a reload. Press `r` to refresh
at once; set `VSAA_STUCK_MINUTES=0` to turn the automatic refresh off.

### What it never approves

Deletes (`Remove-Item`, `rm`, `del`, `rd`, `erase`, …), `Format-*`, `Stop-Computer`,
`Restart-Computer`, `Clear-Content`, and the git commands that lose work or leave the machine:
`push`, `reset --hard`, `clean`, `checkout -- <file>`, `branch -D`. For those it beeps and waits
for you.

The list matches text, so it is a seatbelt, not a guarantee: a command that builds a delete
indirectly (for example inside `pwsh -c "…"`) is not caught. Keep committing often.

### Settings

| Variable | Default | What it does |
|---|---|---|
| `VSAA_PORT` | `9333` | Must match the `--remote-debugging-port` in the VS Code shortcut |
| `VSAA_WEBVIEW` | `gitlab` | Text in the Duo panel's webview address, to pick that panel |
| `VSAA_FRAME` | `agentic\|duo` | Name or address of the frames that hold the chat (served from `http://127.0.0.1:<port>`) |
| `VSAA_BUTTON` | `Approve` | The button text to click |
| `VSAA_EVERY_MS` | `1500` | How often it checks, in milliseconds |
| `VSAA_STUCK_MINUTES` | `3` | Refresh the chat view after this long with no change while Duo is working; `0` = never |
| `VSAA_BUSY` | `working on your request\|please wait` | Text Duo shows while it is working |

### If it connects but never approves

The Duo chat sits several frames deep: the VS Code panel (`vscode-webview://…`), then
`active-frame`, then `agentic-tabs` and `iframe-chat`, which the GitLab extension serves from
`http://127.0.0.1:<port>`. The script searches every frame whose name or address matches
`VSAA_FRAME`. It prints `watching N GitLab Duo frame(s)` when it finds them.

To see the frame names: in VS Code run **Developer: Open Webview Developer Tools**, open the
**Console** tab, and open the context dropdown (it shows `top`). If the chat frames are named
differently, set `VSAA_FRAME` to a word from their names.

### Cautions

- While VS Code runs with the port, any program on this computer can control VS Code through it.
  It is reachable only from this computer, not the network. Check that is acceptable where you
  work.
- It approves in **every** VS Code window that has the Duo panel open.
