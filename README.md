# QA-Testing Framework for Dataforge
---
## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Running Tests](#running-tests)
---
## Overview

This test suite validates Dataforge, an IoT application from Innoveria. Tests are written using pytest, vitest and playwright.
---
## Prerequisites
- Python 3.11+
- Docker (required for the PostgreSQL test container)
- Node.js (required for Vitest and Playwright)
- The project's virtual environment activated

Install dependencies:
```bash
cd Testsuite-Dataforge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install frontend dependencies:
```bash
cd frontend
npm install
```

Verify Docker is running before executing any tests:
```bash
docker info
```
---
## Project Structure
```
Testsuite-Dataforge/
├── backend/
│   ├── conftest.py                  # Shared fixtures, auth mocks, DB setup
│   ├── test_schema.sql              # Schema used to initialize the test DB
│   │
│   ├── test_apis/                   # Integration tests — full HTTP stack
│   │   ├── test_admin_unit.py
│   │   ├── test_sensor_data.py
│   │   └── ...
│   │
│   └── test_libs/
│       └── Unit_tests/              # Unit tests — isolated function tests
│           ├── test_payload_decoders_unit.py
│           └── ...
│
├── frontend/                        # Frontend tests (Vitest + Playwright)
├── logs/                            # Test output logs (auto-created)
├── test.sh                          # Main entry point for running all tests
├── run-e2e.sh                       # Playwright runner (called by test.sh)
├── pyproject.toml                   # Pytest configuration
└── TESTING.md                       # This file
```
The application code being tested lives outside this repository:
```
../dataforge/backend/       # FastAPI app, imported by conftest.py at runtime
```
---
## Running Tests

All tests are run through `test.sh` from the repository root. This is the primary and recommended way to execute the test suite.

```bash
./test.sh
```

The script runs four steps in sequence:

| Step | Tool | What it does |
|------|------|--------------|
| 1 | **Ruff** | Lints the Dataforge backend source |
| 2 | **Pytest** | Runs all backend unit and integration tests |
| 3 | **Vitest** | Runs frontend integration tests |
| 4 | **Playwright** | Runs end-to-end tests |

Each step prints a live status line and writes detailed output to a log file under `logs/`:

| Log file | Contents |
|----------|----------|
| `logs/lint_log.txt` | Ruff linting output |
| `logs/testsuite_log.txt` | Pytest output |
| `logs/vitest_log.txt` | Vitest output |
| `logs/e2e_log.txt` | Playwright output |

The script continues through all steps regardless of individual failures, so you get a full picture in one run. Exit status per step is shown inline:

```
✅ Pytest succeeded after 42s
❌ Playwright: Some of the tests failed after 18s. See logs/e2e_log.txt
```

If a step fails, check the corresponding log file for details.

---

## Running Individual Test Steps (Advanced)

If you need to run a specific part of the suite in isolation during development, you can invoke the tools directly. This is not the recommended workflow — prefer `test.sh` for full runs.

### Pytest only
```bash
pytest backend/
```

### Run a specific file or test
```bash
pytest backend/test_apis/Integration/test_sensor_data.py
pytest backend/test_apis/test_sensor_data.py::TestReadingsFilters::test_filter_by_sensor_euis
```

### Run tests matching a keyword
```bash
pytest -k "sensor"
pytest -k "not admin"
```

### Useful pytest flags
| Flag | Effect |
|------|--------|
| `-v` | Verbose output — shows each test name and result |
| `-x` | Stop after the first failure |
| `--tb=short` | Compact traceback |
| `--tb=long` | Full traceback with local variables |
| `--disable-warnings` | Suppress deprecation warnings |
| `-s` | Show print/log output from tests |
