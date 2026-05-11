#!/usr/bin/env python3
"""
Standalone Test Runner - Web-based GUI
Supports: pytest (backend), vitest + playwright (frontend)
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
FRONTEND_DIR = TEST_DIR / "frontend"
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

        /* Header */
        .header {
            background: #1e1e2e;
            color: white;
            padding: 18px 24px;
        }
        .header h1 { font-size: 17px; font-weight: 600; }
        .header p { font-size: 12px; opacity: 0.5; margin-top: 2px; }

        /* Tabs */
        .tabs {
            display: flex;
            background: #f7f7f8;
            border-bottom: 1px solid #e5e5e5;
        }
        .tab {
            padding: 11px 20px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            background: none;
            color: #888;
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
            transition: color 0.15s;
            display: flex;
            align-items: center;
            gap: 7px;
        }
        .tab:hover { color: #333; }
        .tab.active { color: #1e1e2e; border-bottom-color: #5c6bc0; font-weight: 600; }
        .tab-icon { font-size: 14px; }

        /* Tab panels */
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }

        /* Toolbar */
        .toolbar {
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 10px;
            align-items: center;
            background: #fafafa;
            flex-wrap: wrap;
        }
        select {
            flex: 1;
            min-width: 200px;
            padding: 7px 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            background: white;
        }

        /* Frontend runner selector */
        .runner-pills {
            display: flex;
            gap: 6px;
        }
        .runner-pill {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            border: 1.5px solid #ddd;
            background: white;
            color: #888;
            transition: all 0.15s;
        }
        .runner-pill:hover { border-color: #aaa; color: #444; }
        .runner-pill.active-vitest { border-color: #f59e0b; background: #fffbeb; color: #92400e; }
        .runner-pill.active-playwright { border-color: #06b6d4; background: #ecfeff; color: #0e7490; }

        .btn {
            padding: 7px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: opacity 0.2s;
            white-space: nowrap;
        }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn-run { background: #5c6bc0; color: white; }
        .btn-run:hover:not(:disabled) { background: #4a5ab5; }
        .btn-stop { background: #ef5350; color: white; }
        .btn-stop:hover:not(:disabled) { background: #e53935; }

        /* Output */
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
        .dot-pass { width: 7px; height: 7px; border-radius: 50%; background: #66bb6a; flex-shrink: 0; }
        .test-fail { margin: 6px 0; border: 1px solid #ffcdd2; border-radius: 6px; overflow: hidden; }
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
        .dot-fail { width: 7px; height: 7px; border-radius: 50%; background: #ef5350; flex-shrink: 0; }
        .test-fail-body { padding: 8px 10px; background: white; font-size: 12px; color: #555; }
        .fail-location { margin-bottom: 6px; font-family: -apple-system, sans-serif; }
        .fail-location code {
            background: #f5f5f5; padding: 1px 5px;
            border-radius: 3px; font-family: monospace; font-size: 11px;
        }
        .assertion-block {
            background: #fff8f8;
            border-left: 3px solid #ef9a9a;
            border-radius: 0 4px 4px 0;
            padding: 6px 10px;
            color: #b71c1c;
            white-space: pre-wrap;
            overflow-x: auto;
            word-break: break-word;
        }

        /* Summary bar */
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
        .badge { padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
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

        .footer { padding: 8px 16px; font-size: 11px; color: #bbb; border-top: 1px solid #f0f0f0; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Test Suite Runner</h1>
        <p>{test_dir}</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
        <button class="tab active" onclick="switchTab('backend')">
            <span class="tab-icon">🐍</span> Backend
        </button>
        <button class="tab" onclick="switchTab('frontend')">
            <span class="tab-icon">🌐</span> Frontend
        </button>
    </div>

    <!-- Backend Panel -->
    <div class="tab-panel active" id="panel-backend">
        <div class="toolbar">
            <select id="be-scope"><option value="all">Loading...</option></select>
            <button class="btn btn-run" id="be-runBtn" onclick="runBackend()">Run Tests</button>
            <button class="btn btn-stop" id="be-stopBtn" disabled onclick="stopTests()">Stop</button>
        </div>
        <div class="output-area" id="be-outputArea">
            <span class="placeholder">Ready to run backend tests...</span>
        </div>
        <div class="summary-bar" id="be-summaryBar" style="display:none;"></div>
    </div>

    <!-- Frontend Panel -->
    <div class="tab-panel" id="panel-frontend">
        <div class="toolbar">
            <div class="runner-pills">
                <button class="runner-pill active-vitest" id="pill-vitest" onclick="selectRunner('vitest')">⚡ Vitest</button>
                <button class="runner-pill" id="pill-playwright" onclick="selectRunner('playwright')">🎭 Playwright</button>
            </div>
            <select id="fe-scope"><option value="all">All Tests</option></select>
            <button class="btn btn-run" id="fe-runBtn" onclick="runFrontend()">Run Tests</button>
            <button class="btn btn-stop" id="fe-stopBtn" disabled onclick="stopTests()">Stop</button>
        </div>
        <div class="output-area" id="fe-outputArea">
            <span class="placeholder">Ready to run frontend tests...</span>
        </div>
        <div class="summary-bar" id="fe-summaryBar" style="display:none;"></div>
    </div>

    <div class="footer" id="footer">Test Directory: {test_dir}</div>
</div>

<script>
// ─── State ────────────────────────────────────────────────────────────────────
let activeTab = 'backend';
let activeRunner = 'vitest';
let scopeInterval = null;

// ─── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
    activeTab = tab;
    document.querySelectorAll('.tab').forEach((t, i) => {
        t.classList.toggle('active', (i === 0 && tab === 'backend') || (i === 1 && tab === 'frontend'));
    });
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('panel-' + tab).classList.add('active');
    if (tab === 'frontend') loadFrontendScopes();
}

// ─── Runner selection ─────────────────────────────────────────────────────────
function selectRunner(runner) {
    activeRunner = runner;
    document.getElementById('pill-vitest').className = 'runner-pill' + (runner === 'vitest' ? ' active-vitest' : '');
    document.getElementById('pill-playwright').className = 'runner-pill' + (runner === 'playwright' ? ' active-playwright' : '');
    loadFrontendScopes();
}

// ─── Scope loading ────────────────────────────────────────────────────────────
function startScopePoll() {
    if (scopeInterval) return;
    scopeInterval = setInterval(() => {
        if (activeTab === 'backend') loadBackendScopes();
    }, 5000);
}
function stopScopePoll() { clearInterval(scopeInterval); scopeInterval = null; }

async function loadBackendScopes() {
    try {
        const r = await fetch('/api/scopes?type=backend');
        const d = await r.json();
        const sel = document.getElementById('be-scope');
        sel.innerHTML = '';
        d.scopes.forEach(s => {
            const o = document.createElement('option');
            o.value = s;
            o.textContent = s === 'all' ? 'All Tests' : s;
            sel.appendChild(o);
        });
    } catch(e) {}
}

async function loadFrontendScopes() {
    try {
        const r = await fetch('/api/scopes?type=frontend&runner=' + activeRunner);
        const d = await r.json();
        const sel = document.getElementById('fe-scope');
        sel.innerHTML = '';
        d.scopes.forEach(s => {
            const o = document.createElement('option');
            o.value = s;
            o.textContent = s === 'all' ? 'All Tests' : s;
            sel.appendChild(o);
        });
    } catch(e) {}
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
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

// ─── pytest output parser ─────────────────────────────────────────────────────
function parsePytestOutput(raw) {
    const lines = raw.split('\\n');
    const passed = [], failed = [], errors = [], skipped = [];
    let duration = '';

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

    let inFailures = false, inErrors = false;
    let currentName = null, assertLines = [], locationLine = '';

    function flushFail(bucket) {
        if (currentName) bucket.push({ name: currentName, assertion: assertLines.join('\\n').trim(), location: locationLine });
        currentName = null; assertLines = []; locationLine = '';
    }

    for (const line of lines) {
        if (/^={5,}\\s*FAILURES\\s*={5,}/.test(line)) { inFailures = true; inErrors = false; continue; }
        if (/^={5,}\\s*ERRORS\\s*={5,}/.test(line)) { flushFail(failed); inErrors = true; inFailures = false; continue; }
        if (/^={5,}\\s*(short test summary|warnings summary)/.test(line)) {
            flushFail(inFailures ? failed : errors); inFailures = false; inErrors = false; continue;
        }
        if (inFailures || inErrors) {
            const bucket = inFailures ? failed : errors;
            const hm = line.match(/^_{5,}\\s+(.+?)\\s+_{5,}$/);
            if (hm) { flushFail(bucket); currentName = formatTestName(hm[1].trim()); continue; }
            if (!locationLine && /\\.py:\\d+/.test(line) && !line.trim().startsWith('E ')) {
                const m = line.match(/([\\w./]+\\.py:\\d+)/);
                if (m) locationLine = m[1];
            }
            if (/^\\s*E\\s+/.test(line)) assertLines.push(line.replace(/^\\s*E\\s+/, ''));
        }
    }
    flushFail(failed);

    if (failed.length === 0 && errors.length === 0) {
        for (const line of lines) {
            if (/^FAILED\\s+/.test(line.trim())) {
                const rest = line.replace(/^FAILED\\s+/, '');
                const [tp, ...rp] = rest.split(' - ');
                failed.push({ name: formatTestName(tp.trim()), assertion: rp.join(' - ').trim(), location: '' });
            }
            if (/^ERROR\\s+/.test(line.trim())) {
                const rest = line.replace(/^ERROR\\s+/, '');
                const [tp, ...rp] = rest.split(' - ');
                errors.push({ name: formatTestName(tp.trim()), assertion: rp.join(' - ').trim(), location: '' });
            }
        }
    }
    return { passed, failed, errors, skipped, duration };
}

// ─── Vitest output parser ─────────────────────────────────────────────────────
function parseVitestOutput(raw) {
    const lines = raw.split('\\n');
    const passed = [], failed = [], errors = [], skipped = [];
    let duration = '';

    // Vitest formats: "✓ test name" / "× test name" / "↓ test name (skipped)"
    // Also handles: "PASS src/foo.test.ts" / "FAIL src/foo.test.ts"
    let currentFail = null;
    let errorLines = [];

    function flushFail() {
        if (currentFail) {
            failed.push({ name: currentFail, assertion: errorLines.join('\\n').trim(), location: '' });
            currentFail = null; errorLines = [];
        }
    }

    for (const line of lines) {
        const trimmed = line.trim();

        // Duration line: "Duration  1.23s"
        const dm = trimmed.match(/Duration\\s+(\\d+\\.?\\d*s)/);
        if (dm) { duration = dm[1]; continue; }

        // Passed test: starts with ✓ or √ or "✔"
        if (/^[✓√✔]/.test(trimmed)) {
            flushFail();
            const name = trimmed.replace(/^[✓√✔]\\s*/, '').replace(/\\s+\\d+ms$/, '').trim();
            if (name) passed.push(name);
            continue;
        }

        // Failed test: starts with × or ✕ or "✗" or "FAIL"
        if (/^[×✕✗x]/.test(trimmed) || /^\\s*FAIL\\s/.test(line)) {
            flushFail();
            const name = trimmed.replace(/^[×✕✗x]\\s*/, '').trim();
            if (name && !name.startsWith('FAIL ')) { currentFail = name; continue; }
        }

        // Skipped: ↓ or "skip"
        if (/^↓/.test(trimmed) || /skipped/i.test(trimmed)) {
            const name = trimmed.replace(/^↓\\s*/, '').replace(/\\(skipped\\)/i, '').trim();
            if (name) skipped.push(name);
            continue;
        }

        // Error/assertion lines inside a fail block
        if (currentFail && (trimmed.startsWith('Error:') || trimmed.startsWith('AssertionError') ||
            trimmed.startsWith('Expected') || trimmed.startsWith('Received') ||
            trimmed.startsWith('at ') || /^\\+/.test(trimmed) || /^-/.test(trimmed))) {
            errorLines.push(trimmed);
        }

        // Summary line: "Tests  3 passed | 1 failed"
        const sm = trimmed.match(/Tests\\s+(\\d+)\\s+passed/);
        if (sm && passed.length === 0) {
            // vitest ran but output was minimal — use summary counts as hint
        }
    }
    flushFail();

    return { passed, failed, errors, skipped, duration };
}

// ─── Playwright output parser ─────────────────────────────────────────────────
function parsePlaywrightOutput(raw) {
    const lines = raw.split('\\n');
    const passed = [], failed = [], errors = [], skipped = [];
    let duration = '';
    let currentFail = null;
    let errorLines = [];

    function flushFail() {
        if (currentFail) {
            failed.push({ name: currentFail, assertion: errorLines.join('\\n').trim(), location: '' });
            currentFail = null; errorLines = [];
        }
    }

    for (const line of lines) {
        const trimmed = line.trim();

        // "✓ › test name (123ms)"
        if (/^[✓✔]/.test(trimmed)) {
            flushFail();
            const name = trimmed.replace(/^[✓✔]\\s*[›>]?\\s*/, '').replace(/\\s*\\(\\d+ms\\)$/, '').trim();
            if (name) passed.push(name);
            continue;
        }

        // "✘ › test name" or "× › test name"
        if (/^[✘×✕]/.test(trimmed)) {
            flushFail();
            currentFail = trimmed.replace(/^[✘×✕]\\s*[›>]?\\s*/, '').replace(/\\s*\\(\\d+ms\\)$/, '').trim();
            continue;
        }

        // "–  test name (skipped)"
        if (/^[–—-]\\s/.test(trimmed) || /skipped/i.test(trimmed)) {
            const name = trimmed.replace(/^[–—-]\\s*[›>]?\\s*/, '').replace(/\\(skipped\\)/i, '').trim();
            if (name) skipped.push(name);
            continue;
        }

        if (currentFail && (trimmed.startsWith('Error:') || trimmed.startsWith('expect(') ||
            trimmed.startsWith('Expected') || trimmed.startsWith('Received') ||
            trimmed.startsWith('at '))) {
            errorLines.push(trimmed);
        }

        // Duration: "Finished in 2.3s"
        const dm = trimmed.match(/Finished in (\\d+\\.?\\d*s)/);
        if (dm) duration = dm[1];

        // "X passed, Y failed"
        const sm = trimmed.match(/(\\d+) passed/);
        if (sm) {} // counts handled by individual lines above
    }
    flushFail();
    return { passed, failed, errors, skipped, duration };
}

// ─── Render results ───────────────────────────────────────────────────────────
function renderResults(prefix, passed, failed, errors, skipped, duration) {
    const outputArea = document.getElementById(prefix + '-outputArea');
    const summaryBar = document.getElementById(prefix + '-summaryBar');
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
                if (t.location) body.innerHTML = `<div class="fail-location">at <code>${escHtml(t.location)}</code></div>`;
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

// ─── Run backend ──────────────────────────────────────────────────────────────
async function runBackend() {
    stopScopePoll();
    const runBtn = document.getElementById('be-runBtn');
    const stopBtn = document.getElementById('be-stopBtn');
    const outputArea = document.getElementById('be-outputArea');
    const summaryBar = document.getElementById('be-summaryBar');

    runBtn.disabled = true; stopBtn.disabled = false;
    summaryBar.style.display = 'none';
    outputArea.innerHTML = '<span style="color:#888;"><span class="spinner"></span> Running pytest...</span>';

    const scope = document.getElementById('be-scope').value;
    const start = Date.now();
    try {
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'backend', scope })
        });
        const text = await response.text();
        const { passed, failed, errors, skipped, duration } = parsePytestOutput(text);
        renderResults('be', passed, failed, errors, skipped, duration || ((Date.now() - start) / 1000).toFixed(2) + 's');
    } catch(e) {
        outputArea.innerHTML = `<span style="color:#c62828;">Error: ${escHtml(e.message)}</span>`;
    } finally {
        runBtn.disabled = false; stopBtn.disabled = true;
        startScopePoll();
    }
}

// ─── Run frontend ─────────────────────────────────────────────────────────────
async function runFrontend() {
    stopScopePoll();
    const runBtn = document.getElementById('fe-runBtn');
    const stopBtn = document.getElementById('fe-stopBtn');
    const outputArea = document.getElementById('fe-outputArea');
    const summaryBar = document.getElementById('fe-summaryBar');

    runBtn.disabled = true; stopBtn.disabled = false;
    summaryBar.style.display = 'none';
    outputArea.innerHTML = `<span style="color:#888;"><span class="spinner"></span> Running ${activeRunner}...</span>`;

    const scope = document.getElementById('fe-scope').value;
    const start = Date.now();
    try {
        const response = await fetch('/api/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'frontend', runner: activeRunner, scope })
        });
        const text = await response.text();
        const parser = activeRunner === 'vitest' ? parseVitestOutput : parsePlaywrightOutput;
        const { passed, failed, errors, skipped, duration } = parser(text);
        renderResults('fe', passed, failed, errors, skipped, duration || ((Date.now() - start) / 1000).toFixed(2) + 's');
    } catch(e) {
        outputArea.innerHTML = `<span style="color:#c62828;">Error: ${escHtml(e.message)}</span>`;
    } finally {
        runBtn.disabled = false; stopBtn.disabled = true;
        startScopePoll();
    }
}

// ─── Stop ─────────────────────────────────────────────────────────────────────
async function stopTests() {
    try { await fetch('/api/stop', { method: 'POST' }); } catch(e) {}
    ['be', 'fe'].forEach(p => {
        const r = document.getElementById(p + '-runBtn');
        const s = document.getElementById(p + '-stopBtn');
        if (r) r.disabled = false;
        if (s) s.disabled = true;
    });
    startScopePoll();
}

// ─── Init ─────────────────────────────────────────────────────────────────────
loadBackendScopes();
startScopePoll();
</script>
"""


def get_backend_scopes():
    scopes = ["all"]
    backend_dir = TEST_DIR / "backend"
    if not backend_dir.exists():
        backend_dir = TEST_DIR

    for root, dirs, files in os.walk(backend_dir):
        if any(skip in root for skip in [".pytest_cache", "__pycache__", ".git", ".venv"]):
            continue
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, file), backend_dir)
                scopes.append(rel)
        rel_root = os.path.relpath(root, backend_dir)
        if rel_root != "." and any(p in rel_root.lower() for p in ["test_", "tests", "integration", "unit_"]):
            scopes.append(rel_root)

    return sorted(list(set(scopes)))


def get_frontend_scopes(runner: str):
    scopes = ["all"]
    if not FRONTEND_DIR.exists():
        return scopes

    if runner == "vitest":
        for root, dirs, files in os.walk(FRONTEND_DIR):
            if any(skip in root for skip in ["node_modules", ".git", "dist"]):
                continue
            for file in files:
                if file.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
                    rel = os.path.relpath(os.path.join(root, file), FRONTEND_DIR)
                    scopes.append(rel)
            rel_root = os.path.relpath(root, FRONTEND_DIR)
            if rel_root != "." and any(p in rel_root.lower() for p in ["test_", "tests", "__tests__"]):
                scopes.append(rel_root)

    elif runner == "playwright":
        for root, dirs, files in os.walk(FRONTEND_DIR):
            if any(skip in root for skip in ["node_modules", ".git", "dist"]):
                continue
            for file in files:
                if file.endswith((".spec.ts", ".spec.tsx", ".e2e.ts")):
                    rel = os.path.relpath(os.path.join(root, file), FRONTEND_DIR)
                    scopes.append(rel)

    return sorted(list(set(scopes)))


class TestRunnerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        query = urlparse(self.path).query
        params = dict(p.split("=") for p in query.split("&") if "=" in p)

        if path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = HTML_TEMPLATE.replace("{test_dir}", str(TEST_DIR))
            self.wfile.write(html.encode())

        elif path == "/api/scopes":
            test_type = params.get("type", "backend")
            runner = params.get("runner", "vitest")
            scopes = get_backend_scopes() if test_type == "backend" else get_frontend_scopes(runner)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
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

            test_type = data.get("type", "backend")
            scope = data.get("scope", "all")
            runner = data.get("runner", "vitest")

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            if test_type == "backend":
                backend_dir = TEST_DIR / "backend"
                if not backend_dir.exists():
                    backend_dir = TEST_DIR
                cmd = ["pytest", "-v", "--tb=short", "--disable-warnings"]
                if scope != "all":
                    cmd.append(str(backend_dir / scope))
                cwd = backend_dir

            elif test_type == "frontend":
                if runner == "vitest":
                    cmd = ["npm", "run", "test:unit"]
                    if scope != "all":
                        cmd.append(scope)
                elif runner == "playwright":
                    cmd = ["npm", "run", "test:e2e"]
                    if scope != "all":
                        cmd.append(scope)
                cwd = FRONTEND_DIR

            try:
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
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
    print(f"📁 Backend tests: {TEST_DIR / 'backend'}")
    print(f"📁 Frontend tests: {FRONTEND_DIR}")
    print(f"Press Ctrl+C to stop\n")

    def open_browser():
        time.sleep(1)
        webbrowser.open(f"http://127.0.0.1:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Test Runner stopped. Goodbye!")


if __name__ == "__main__":
    start_server()