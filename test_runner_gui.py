#!/usr/bin/env python3
"""
Standalone Test Runner - Web-based GUI
No dependencies needed - runs in your browser!
"""

import subprocess
import os
import json
import threading
import webbrowser
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

TEST_DIR = Path(__file__).parent
PORT = 9999
RUNNING = {"process": None}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Suite Runner</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f0f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.12);
            width: 100%;
            max-width: 900px;
            overflow: hidden;
        }
        .header {
            background: #1e1e2e;
            color: white;
            padding: 20px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header h1 { font-size: 18px; font-weight: 600; }
        .header p { font-size: 13px; opacity: 0.6; margin-top: 2px; }
        .toolbar {
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 10px;
            align-items: center;
            background: #fafafa;
        }
        select {
            flex: 1;
            padding: 7px 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            background: white;
        }
        .btn {
            padding: 7px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: opacity 0.2s;
        }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn-run { background: #5c6bc0; color: white; }
        .btn-run:hover:not(:disabled) { background: #4a5ab5; }
        .btn-stop { background: #ef5350; color: white; }
        .btn-stop:hover:not(:disabled) { background: #e53935; }
        .output-area {
            padding: 16px;
            min-height: 360px;
            max-height: 480px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12.5px;
            line-height: 1.6;
        }
        .placeholder { color: #aaa; font-style: italic; }
        .section-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #999;
            margin: 14px 0 6px;
            font-family: -apple-system, sans-serif;
        }
        .section-label:first-child { margin-top: 0; }
        .passes-toggle {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 0;
            color: #888;
            font-size: 12px;
            cursor: pointer;
            font-family: -apple-system, sans-serif;
            background: none;
            border: none;
            text-align: left;
        }
        .passes-toggle:hover { color: #555; }
        .passes-list { margin-top: 4px; }
        .test-pass {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 2px 0;
            color: #888;
            font-size: 12px;
        }
        .dot-pass {
            width: 7px; height: 7px;
            border-radius: 50%;
            background: #66bb6a;
            flex-shrink: 0;
        }
        .test-fail {
            margin: 6px 0;
            border: 1px solid #ffcdd2;
            border-radius: 6px;
            overflow: hidden;
        }
        .test-fail-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 7px 10px;
            background: #fff5f5;
            color: #c62828;
            font-size: 12.5px;
            font-weight: 600;
        }
        .dot-fail {
            width: 7px; height: 7px;
            border-radius: 50%;
            background: #ef5350;
            flex-shrink: 0;
        }
        .test-fail-body {
            padding: 8px 10px;
            background: white;
            font-size: 12px;
            color: #555;
        }
        .fail-location {
            margin-bottom: 6px;
            font-family: -apple-system, sans-serif;
        }
        .fail-location code {
            background: #f5f5f5;
            padding: 1px 5px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 11px;
        }
        .assertion-block {
            background: #fff8f8;
            border-left: 3px solid #ef9a9a;
            border-radius: 0 4px 4px 0;
            padding: 6px 10px;
            color: #b71c1c;
            white-space: pre;
            overflow-x: auto;
        }
        .summary-bar {
            padding: 10px 16px;
            border-top: 1px solid #eee;
            background: #fafafa;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 13px;
            color: #888;
            flex-wrap: wrap;
        }
        .badge {
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-pass { background: #e8f5e9; color: #2e7d32; }
        .badge-fail { background: #ffebee; color: #c62828; }
        .badge-skip { background: #fff8e1; color: #f57f17; }
        .badge-error { background: #fce4ec; color: #880e4f; }
        .spinner {
            display: inline-block;
            width: 10px; height: 10px;
            border: 2px solid #ddd;
            border-top-color: #5c6bc0;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            margin-right: 6px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .footer {
            padding: 8px 16px;
            font-size: 11px;
            color: #bbb;
            border-top: 1px solid #f0f0f0;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>Test Suite Runner</h1>
            <p>Test Directory: {test_dir}</p>
        </div>
    </div>
    <div class="toolbar">
        <select id="scope"><option value="all">Loading...</option></select>
        <button class="btn btn-run" id="runBtn">Run Tests</button>
        <button class="btn btn-stop" id="stopBtn" disabled>Stop</button>
    </div>
    <div class="output-area" id="outputArea">
        <span class="placeholder">Ready to run tests...</span>
    </div>
    <div class="summary-bar" id="summaryBar" style="display:none;"></div>
    <div class="footer" id="footer"></div>
</div>
<script>
const scopeSelect = document.getElementById('scope');
const runBtn = document.getElementById('runBtn');
const stopBtn = document.getElementById('stopBtn');
const outputArea = document.getElementById('outputArea');
const summaryBar = document.getElementById('summaryBar');

let scopeInterval = null;

function startScopePoll() {
    if (scopeInterval) return;
    scopeInterval = setInterval(loadScopes, 5000);
}

function stopScopePoll() {
    clearInterval(scopeInterval);
    scopeInterval = null;
}

async function loadScopes() {
    try {
        const r = await fetch('/api/scopes');
        const d = await r.json();
        scopeSelect.innerHTML = '';
        d.scopes.forEach(s => {
            const o = document.createElement('option');
            o.value = s;
            o.textContent = s === 'all' ? 'All Tests' : s;
            scopeSelect.appendChild(o);
        });
    } catch(e) {}
}

function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function badge(text, cls) {
    return `<span class="badge ${cls}">${text}</span>`;
}

function formatTestName(raw) {
    const parts = raw.split('::');
    if (parts.length >= 3) return parts.slice(1).join(' :: ');
    if (parts.length === 2) return parts[1];
    return raw.split('/').pop() || raw;
}

function parseOutput(raw) {
    const lines = raw.split('\\n');
    const passed = [], failed = [], errors = [], skipped = [];
    let duration = '';

    // Step 1: collect PASSED/SKIPPED from verbose lines
    for (const line of lines) {
        if (/\\bPASSED\\b/.test(line)) {
            const name = formatTestName(line.split(/\\s+PASSED/)[0].trim());
            if (name) passed.push(name);
        } else if (/\\bSKIPPED\\b/.test(line)) {
            const name = formatTestName(line.split(/\\s+SKIPPED/)[0].trim());
            if (name) skipped.push(name);
        }
        const dm = line.match(/in (\\d+\\.?\\d*s)/);
        if (dm && /passed|failed|error/.test(line)) duration = dm[1];
    }

    // Step 2: parse FAILURES / ERRORS sections
    let inFailures = false;
    let inErrors = false;
    let currentName = null;
    let assertLines = [];
    let locationLine = '';

    function flushFail(bucket) {
        if (currentName) {
            bucket.push({
                name: currentName,
                assertion: assertLines.join('\\n').trim(),
                location: locationLine
            });
        }
        currentName = null;
        assertLines = [];
        locationLine = '';
    }

    for (const line of lines) {
        if (/^={5,}\\s*FAILURES\\s*={5,}/.test(line)) {
            inFailures = true; inErrors = false; continue;
        }
        if (/^={5,}\\s*ERRORS\\s*={5,}/.test(line)) {
            flushFail(failed); inErrors = true; inFailures = false; continue;
        }
        if (/^={5,}\\s*(short test summary|warnings summary)/.test(line)) {
            flushFail(inFailures ? failed : errors);
            inFailures = false; inErrors = false; continue;
        }

        if (inFailures || inErrors) {
            const bucket = inFailures ? failed : errors;
            const headerMatch = line.match(/^_{5,}\\s+(.+?)\\s+_{5,}$/);
            if (headerMatch) {
                flushFail(bucket);
                currentName = formatTestName(headerMatch[1].trim());
                continue;
            }
            if (!locationLine && /\\.py:\\d+/.test(line) && !line.trim().startsWith('E ')) {
                const m = line.match(/([\\w./]+\\.py:\\d+)/);
                if (m) locationLine = m[1];
            }
            if (/^\\s*E\\s+/.test(line)) {
                assertLines.push(line.replace(/^\\s*E\\s+/, ''));
            }
        }
    }
    flushFail(failed);

    // Step 3: fallback to short summary lines if sections yielded nothing
    if (failed.length === 0 && errors.length === 0) {
        for (const line of lines) {
            if (/^FAILED\\s+/.test(line.trim())) {
                const rest = line.replace(/^FAILED\\s+/, '');
                const [testPath, ...reasonParts] = rest.split(' - ');
                failed.push({ name: formatTestName(testPath.trim()), assertion: reasonParts.join(' - ').trim(), location: '' });
            }
            if (/^ERROR\\s+/.test(line.trim())) {
                const rest = line.replace(/^ERROR\\s+/, '');
                const [testPath, ...reasonParts] = rest.split(' - ');
                errors.push({ name: formatTestName(testPath.trim()), assertion: reasonParts.join(' - ').trim(), location: '' });
            }
        }
    }

    return { passed, failed, errors, skipped, duration };
}

function renderResults(passed, failed, errors, skipped, duration) {
    outputArea.innerHTML = '';
    summaryBar.style.display = 'flex';

    function sectionLabel(text) {
        const d = document.createElement('div');
        d.className = 'section-label';
        d.textContent = text;
        outputArea.appendChild(d);
    }

    if (failed.length > 0) {
        sectionLabel(`Failed (${failed.length})`);
        failed.forEach(t => {
            const wrap = document.createElement('div');
            wrap.className = 'test-fail';
            const header = document.createElement('div');
            header.className = 'test-fail-header';
            header.innerHTML = `<div class="dot-fail"></div>${escHtml(t.name)}`;
            wrap.appendChild(header);
            if (t.assertion || t.location) {
                const body = document.createElement('div');
                body.className = 'test-fail-body';
                if (t.location) {
                    body.innerHTML = `<div class="fail-location">at <code>${escHtml(t.location)}</code></div>`;
                }
                if (t.assertion) {
                    const ab = document.createElement('div');
                    ab.className = 'assertion-block';
                    ab.textContent = t.assertion;
                    body.appendChild(ab);
                }
                wrap.appendChild(body);
            }
            outputArea.appendChild(wrap);
        });
    }

    if (errors.length > 0) {
        sectionLabel(`Errors (${errors.length})`);
        errors.forEach(t => {
            const wrap = document.createElement('div');
            wrap.className = 'test-fail';
            wrap.innerHTML = `<div class="test-fail-header"><div class="dot-fail"></div>${escHtml(t.name)}</div>`;
            if (t.assertion) {
                const body = document.createElement('div');
                body.className = 'test-fail-body';
                const ab = document.createElement('div');
                ab.className = 'assertion-block';
                ab.textContent = t.assertion;
                body.appendChild(ab);
                wrap.appendChild(body);
            }
            outputArea.appendChild(wrap);
        });
    }

    if (passed.length > 0) {
        sectionLabel(`Passed (${passed.length})`);
        const toggle = document.createElement('button');
        toggle.className = 'passes-toggle';
        toggle.innerHTML = `<span class="tog-arrow">&#9654;</span> Show ${passed.length} passing test${passed.length !== 1 ? 's' : ''}`;
        outputArea.appendChild(toggle);
        const list = document.createElement('div');
        list.className = 'passes-list';
        list.style.display = 'none';
        passed.forEach(name => {
            const row = document.createElement('div');
            row.className = 'test-pass';
            row.innerHTML = `<div class="dot-pass"></div>${escHtml(name)}`;
            list.appendChild(row);
        });
        outputArea.appendChild(list);
        toggle.addEventListener('click', () => {
            const open = list.style.display !== 'none';
            list.style.display = open ? 'none' : 'block';
            toggle.querySelector('.tog-arrow').innerHTML = open ? '&#9654;' : '&#9660;';
        });
    }

    if (skipped.length > 0) {
        sectionLabel(`Skipped (${skipped.length})`);
        skipped.forEach(name => {
            const row = document.createElement('div');
            row.className = 'test-pass';
            row.style.color = '#bbb';
            row.innerHTML = `<div class="dot-pass" style="background:#e0e0e0;"></div>${escHtml(name)}`;
            outputArea.appendChild(row);
        });
    }

    if (!passed.length && !failed.length && !errors.length && !skipped.length) {
        outputArea.innerHTML = '<span style="color:#c62828;">Could not parse test output.</span>';
    }

    const total = passed.length + failed.length + errors.length + skipped.length;
    let html = `<span>${total} test${total !== 1 ? 's' : ''}</span>`;
    if (duration) html += `<span>${duration}</span>`;
    if (passed.length)  html += badge(`${passed.length} passed`, 'badge-pass');
    if (failed.length)  html += badge(`${failed.length} failed`, 'badge-fail');
    if (errors.length)  html += badge(`${errors.length} error${errors.length > 1 ? 's' : ''}`, 'badge-error');
    if (skipped.length) html += badge(`${skipped.length} skipped`, 'badge-skip');
    summaryBar.innerHTML = html;
}

async function runTests() {
    stopScopePoll();
    runBtn.disabled = true;
    stopBtn.disabled = false;
    summaryBar.style.display = 'none';
    outputArea.innerHTML = '<span style="color:#888;"><span class="spinner"></span> Running tests...</span>';

    const scope = scopeSelect.value;
    const start = Date.now();

    try {
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scope })
        });
        const text = await response.text();
        const { passed, failed, errors, skipped, duration } = parseOutput(text);
        const elapsed = duration || ((Date.now() - start) / 1000).toFixed(2) + 's';
        renderResults(passed, failed, errors, skipped, elapsed);
    } catch (e) {
        outputArea.innerHTML = `<span style="color:#c62828;">Error: ${escHtml(e.message)}</span>`;
    } finally {
        runBtn.disabled = false;
        stopBtn.disabled = true;
        startScopePoll();
    }
}

async function stopTests() {
    try { await fetch('/api/stop', { method: 'POST' }); } catch(e) {}
    runBtn.disabled = false;
    stopBtn.disabled = true;
    startScopePoll();
}

runBtn.addEventListener('click', runTests);
stopBtn.addEventListener('click', stopTests);
loadScopes();
startScopePoll();
</script>
"""


def get_test_scopes():
    """Dynamically discover test scopes."""
    scopes = ["all"]

    if TEST_DIR.exists():
        for root, dirs, files in os.walk(TEST_DIR):
            if any(skip in root for skip in [".pytest_cache", "__pycache__", ".git", ".venv"]):
                continue

            rel_root = os.path.relpath(root, TEST_DIR)
            if rel_root != "." and any(pattern in rel_root.lower() for pattern in ["test_", "tests", "integration", "unit_"]):
                scopes.append(rel_root)

            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    rel_file = os.path.relpath(os.path.join(root, file), TEST_DIR)
                    scopes.append(rel_file)

    return sorted(list(set(scopes)))


class TestRunnerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = HTML_TEMPLATE.replace("{test_dir}", str(TEST_DIR))
            self.wfile.write(html.encode())

        elif path == "/api/scopes":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            scopes = get_test_scopes()
            self.wfile.write(json.dumps({"scopes": scopes}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())
            scope = data.get("scope", "all")

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            cmd = ["pytest", "-v", "--tb=short", "--disable-warnings"]
            if scope != "all":
                cmd.append(str(TEST_DIR / scope))

            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=TEST_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                RUNNING["process"] = process

                for line in iter(process.stdout.readline, ''):
                    self.wfile.write(line.encode())
                    self.wfile.flush()

                process.wait()
                RUNNING["process"] = None

            except Exception as e:
                self.wfile.write(f"ERROR: {str(e)}\n".encode())
                RUNNING["process"] = None

        elif path == "/api/stop":
            if RUNNING["process"]:
                RUNNING["process"].terminate()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"stopped": True}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_server():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), TestRunnerHandler)
    print(f"\n✅ Test Runner is ready!")
    print(f"🌐 Opening http://127.0.0.1:{PORT} in your browser...")
    print(f"Press Ctrl+C to stop\n")

    def open_browser():
        time.sleep(1)
        webbrowser.open(f"http://127.0.0.1:{PORT}")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Test Runner stopped. Goodbye!")


if __name__ == "__main__":
    start_server()