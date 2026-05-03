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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

TEST_DIR = Path(__file__).parent
PORT = 9999
RUNNING = {"process": None}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧪 Test Suite Runner</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 900px;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .content {
            padding: 30px;
        }
        
        .control-panel {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        label {
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }
        
        select {
            flex: 1;
            min-width: 250px;
            padding: 10px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        
        select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .btn-run {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            flex: 1;
            min-width: 120px;
        }
        
        .btn-run:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-stop {
            background: #ff6b6b;
            color: white;
            flex: 0;
        }
        
        .btn-stop:hover:not(:disabled) {
            background: #ff5252;
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .status {
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-weight: 600;
            font-size: 14px;
            display: none;
        }
        
        .status.show {
            display: block;
        }
        
        .status.info {
            background: #e3f2fd;
            color: #1976d2;
            border-left: 4px solid #1976d2;
        }
        
        .status.success {
            background: #e8f5e9;
            color: #388e3c;
            border-left: 4px solid #388e3c;
        }
        
        .status.error {
            background: #ffebee;
            color: #d32f2f;
            border-left: 4px solid #d32f2f;
        }
        
        .output-container {
            background: #1e1e1e;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        #output {
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
            color: #d4d4d4;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .line-success { color: #4ec9b0; }
        .line-error { color: #f48771; }
        .line-info { color: #9cdcfe; }
        .line-warning { color: #ce9178; }
        .line-pass { color: #89d185; }
        .line-fail { color: #f48771; }
        
        .footer {
            padding: 15px 30px;
            background: #f5f5f5;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }
        
        @media (max-width: 600px) {
            .container {
                max-width: 100%;
            }
            
            .control-panel {
                flex-direction: column;
            }
            
            .button-group {
                width: 100%;
            }
            
            .btn-run, .btn-stop {
                flex: 1;
            }
            
            #output {
                height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Test Suite Runner</h1>
            <p>Run your tests with a single click - no terminal needed!</p>
        </div>
        
        <div class="content">
            <div class="control-panel">
                <label for="scope">Select Tests:</label>
                <select id="scope">
                    <option value="all">Loading...</option>
                </select>
                <div class="button-group">
                    <button class="btn-run" id="runBtn">▶ Run Tests</button>
                    <button class="btn-stop" id="stopBtn" disabled>⏹ Stop</button>
                </div>
            </div>
            
            <div id="status" class="status"></div>
            
            <div class="output-container">
                <pre id="output">Ready to run tests...</pre>
            </div>
        </div>
        
        <div class="footer">
            📁 Test Directory: {test_dir}
        </div>
    </div>
    
    <script>
        const scopeSelect = document.getElementById('scope');
        const runBtn = document.getElementById('runBtn');
        const stopBtn = document.getElementById('stopBtn');
        const output = document.getElementById('output');
        const statusDiv = document.getElementById('status');
        let isRunning = false;
        
        // Load available test scopes
        async function loadScopes() {
            try {
                const response = await fetch('/api/scopes');
                const data = await response.json();
                
                scopeSelect.innerHTML = '';
                data.scopes.forEach(scope => {
                    const option = document.createElement('option');
                    option.value = scope;
                    option.textContent = scope === 'all' ? '📦 All Tests' : scope;
                    scopeSelect.appendChild(option);
                });
            } catch (error) {
                showStatus('Error loading test scopes', 'error');
            }
        }
        
        function showStatus(message, type) {
            statusDiv.className = `status show ${type}`;
            statusDiv.textContent = message;
        }
        
        function clearOutput() {
            output.textContent = '';
        }
        
        function addOutput(line, className = '') {
            // Just display the line as-is (already filtered by backend)
            const className_map = {
                'PASSED': 'line-pass',
                'FAILED': 'line-fail',
                '❌': 'line-fail',
                '✅': 'line-pass',
                'E ': 'line-error',
            };
            
            let lineClass = className;
            for (const [key, cls] of Object.entries(className_map)) {
                if (line.includes(key)) {
                    lineClass = cls;
                    break;
                }
            }
            
            const span = document.createElement('span');
            if (lineClass) span.className = lineClass;
            span.textContent = line + '\\n';
            output.appendChild(span);
            output.parentElement.scrollTop = output.parentElement.scrollHeight;
        }
        
        async function runTests() {
            if (isRunning) return;
            
            isRunning = true;
            runBtn.disabled = true;
            stopBtn.disabled = false;
            clearOutput();
            
            const scope = scopeSelect.value;
            showStatus(`🚀 Running tests for: ${scope}`, 'info');
            
            try {
                const response = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scope })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                let fullOutput = '';
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    fullOutput += chunk;
                    
                    // Process line by line
                    const lines = fullOutput.split('\\n');
                    for (let i = 0; i < lines.length - 1; i++) {
                        addOutput(lines[i]);
                    }
                    fullOutput = lines[lines.length - 1];
                }
                
                if (fullOutput) addOutput(fullOutput);
                
                const data = await response.json().catch(() => ({}));
                if (data.success !== undefined) {
                    if (data.success) {
                        showStatus('✅ All tests passed!', 'success');
                    } else {
                        showStatus(`❌ Tests failed (exit code ${data.code})`, 'error');
                    }
                }
            } catch (error) {
                addOutput('Error: ' + error.message);
                showStatus('Error running tests', 'error');
            } finally {
                isRunning = false;
                runBtn.disabled = false;
                stopBtn.disabled = true;
            }
        }
        
        async function stopTests() {
            try {
                await fetch('/api/stop', { method: 'POST' });
                showStatus('⏹ Tests stopped', 'warning');
            } catch (error) {
                console.error('Error stopping tests:', error);
            }
        }
        
        runBtn.addEventListener('click', runTests);
        stopBtn.addEventListener('click', stopTests);
        
        // Load scopes on startup
        loadScopes();
        
        // Refresh scopes every 5 seconds
        setInterval(loadScopes, 5000);
    </script>
</body>
</html>
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
        """Handle GET requests."""
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
        """Handle POST requests."""
        path = urlparse(self.path).path
        
        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())
            scope = data.get("scope", "all")
            
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
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
                    if " PASSED" in line:
                        test_name = line.split(" PASSED")[0].strip()
                        output_line = f"✅ {test_name}"
                        self.wfile.write(f"{output_line}\n".encode())
                        self.wfile.flush()
                    
                    elif " FAILED" in line:
                        test_name = line.split(" FAILED")[0].strip()
                        output_line = f"❌ {test_name}"
                        self.wfile.write(f"{output_line}\n".encode())
                        self.wfile.flush()
                
                process.wait()
                success = process.returncode == 0
                self.wfile.write(f"\n{'='*60}\n".encode())
                result = {
                    "success": success,
                    "code": process.returncode,
                    "message": "✅ All tests passed!" if success else f"❌ Some tests failed"
                }
                self.wfile.write(json.dumps(result).encode())
                RUNNING["process"] = None
            
            except Exception as e:
                self.wfile.write(f"Error: {str(e)}".encode())
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
        """Suppress default logging."""
        pass


def start_server():
    """Start the web server."""
    server = HTTPServer(("127.0.0.1", PORT), TestRunnerHandler)
    print(f"\n✅ Test Runner is ready!")
    print(f"🌐 Opening http://127.0.0.1:{PORT} in your browser...")
    print(f"Press Ctrl+C to stop\n")
    
    # Open browser after a short delay
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
