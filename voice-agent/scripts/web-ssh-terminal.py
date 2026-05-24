#!/usr/bin/env python3
"""
Simple web-based SSH terminal for accessing GCP VMs.
Serve this with: python3 server.py
Then open: http://localhost:8888
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

try:
    import paramiko
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    import uvicorn
except ImportError:
    print("Install: pip install paramiko fastapi uvicorn python-multipart")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

SSH_KEY_PATH = os.environ.get("SSH_KEY", os.path.expanduser("~/.ssh/id_rsa"))
SSH_HOSTS = {
    "sailly-1": "sailly-1.internal",
    "sailly-2": "sailly-2.internal",
}
SSH_USER = os.environ.get("SSH_USER", "charles2")
SSH_PORT = int(os.environ.get("SSH_PORT", "22"))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sailly VM SSH Terminal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #00ff00;
            padding: 10px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #00ffff;
            margin-bottom: 10px;
        }
        .controls {
            margin-bottom: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        select, button {
            padding: 8px 12px;
            background: #333;
            border: 1px solid #00ff00;
            color: #00ff00;
            cursor: pointer;
            font-family: monospace;
        }
        button:hover {
            background: #00ff00;
            color: #000;
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        #terminal {
            background: #000;
            border: 2px solid #00ff00;
            padding: 10px;
            height: 600px;
            overflow-y: auto;
            margin-bottom: 10px;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 12px;
            line-height: 1.4;
        }
        #input {
            width: 100%;
            background: #000;
            border: 1px solid #00ff00;
            color: #00ff00;
            padding: 8px;
            font-family: monospace;
        }
        .status {
            margin-top: 10px;
            padding: 5px;
            border-radius: 3px;
        }
        .status.connected {
            background: #0f0;
            color: #000;
        }
        .status.disconnected {
            background: #f00;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖥️ Sailly VM SSH Terminal</h1>
        <div class="controls">
            <select id="hostSelect">
                <option value="">-- Select Host --</option>
                <option value="sailly-1">sailly-1.internal</option>
                <option value="sailly-2">sailly-2.internal</option>
            </select>
            <button id="connectBtn" onclick="connect()">Connect</button>
            <button id="disconnectBtn" onclick="disconnect()" disabled>Disconnect</button>
            <span id="status" class="status disconnected">Disconnected</span>
        </div>
        <div id="terminal"></div>
        <input id="input" type="text" placeholder="Enter command (e.g., systemctl status sailly-voice-agent)" 
               onkeypress="if(event.key==='Enter') sendCommand()" disabled>
    </div>
    <script>
        let ws = null;
        const terminalEl = document.getElementById('terminal');
        const inputEl = document.getElementById('input');
        const hostSelect = document.getElementById('hostSelect');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const statusEl = document.getElementById('status');

        function connect() {
            const host = hostSelect.value;
            if (!host) {
                alert('Please select a host');
                return;
            }
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${location.host}/ws?host=${host}`;
            
            ws = new WebSocket(url);
            ws.onopen = () => {
                terminalEl.innerHTML += '<span style="color: #0f0;">Connected to ' + host + '</span>\\n';
                inputEl.disabled = false;
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                statusEl.textContent = 'Connected: ' + host;
                statusEl.className = 'status connected';
                inputEl.focus();
            };
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                terminalEl.innerHTML += data.data.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                terminalEl.scrollTop = terminalEl.scrollHeight;
            };
            ws.onerror = (e) => {
                terminalEl.innerHTML += '<span style="color: #f00;">Error: ' + e + '</span>\\n';
                statusEl.textContent = 'Error';
                statusEl.className = 'status disconnected';
            };
            ws.onclose = () => {
                terminalEl.innerHTML += '<span style="color: #f00;">Disconnected</span>\\n';
                inputEl.disabled = true;
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'status disconnected';
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
            }
        }

        function sendCommand() {
            const cmd = inputEl.value;
            if (!cmd.trim()) return;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ command: cmd }));
                terminalEl.innerHTML += '<span style="color: #00ffff;">$ ' + cmd.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</span>\\n';
                inputEl.value = '';
                terminalEl.scrollTop = terminalEl.scrollHeight;
            }
        }
    </script>
</body>
</html>
"""


class SSHTerminal:
    def __init__(self, host, user, key_path, port=22):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.port = port
        self.client = None
        self.channel = None

    async def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.user,
                key_filename=self.key_path,
                timeout=10,
            )
            logger.info(f"Connected to {self.host}")
            return True
        except Exception as e:
            logger.error(f"SSH connect failed: {e}")
            return False

    async def execute(self, command: str) -> str:
        try:
            if not self.client:
                return "Not connected\n"
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode("utf-8", errors="ignore")
            error = stderr.read().decode("utf-8", errors="ignore")
            return output + error
        except Exception as e:
            logger.error(f"Exec failed: {e}")
            return f"Error: {e}\n"

    def close(self):
        if self.client:
            self.client.close()


@app.get("/")
async def root():
    return HTMLResponse(HTML_TEMPLATE)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    host_key = websocket.query_params.get("host")
    if not host_key or host_key not in SSH_HOSTS:
        await websocket.close(code=1008, reason="Invalid host")
        return

    host = SSH_HOSTS[host_key]
    terminal = SSHTerminal(host, SSH_USER, SSH_KEY_PATH, SSH_PORT)

    if not await terminal.connect():
        await websocket.accept()
        await websocket.send_json({"data": "Failed to connect to SSH server\n"})
        await websocket.close()
        return

    await websocket.accept()
    await websocket.send_json(
        {"data": f"Connected to {host_key} ({host})\n$ "}
    )

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            command = msg.get("command", "").strip()
            if command:
                output = await terminal.execute(command)
                await websocket.send_json({"data": output + "$ "})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        terminal.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    print(f"Starting SSH terminal web server on http://localhost:{port}")
    print(f"SSH key: {SSH_KEY_PATH}")
    print(f"SSH user: {SSH_USER}")
    uvicorn.run(app, host="0.0.0.0", port=port)
