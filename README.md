# QA-Testing Framework for Dataforge
---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Running Tests](#running-tests)
5. [Test Types](#test-types)
6. [The conftest.py in depth](#the-conftestpy-in-depth)
7. [Writing New Tests](#writing-new-tests)
8. [Fixtures Reference](#fixtures-reference)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The test suite validates the Dataforge backend API — a FastAPI application backed by a PostgreSQL database. Tests are written with [pytest](https://pytest.org) and live in the `backend/` directory of this repository, separate from the application source which lives in `../dataforge/backend/`.

The suite uses a real PostgreSQL instance (via Docker, managed by `testcontainers`) for integration tests, and mock-based isolation for unit tests. Authentication and authorization are bypassed in all tests through FastAPI's dependency override system.

---

## Prerequisites

- Python 3.11+
- Docker (required for the PostgreSQL test container)
- The project's virtual environment activated

Install dependencies:

```bash
cd Testsuite-Dataforge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
├── pyproject.toml                   # Pytest configuration
└── TESTING.md                       # This file
```

The application code being tested lives outside this repository:

```
../dataforge/backend/       # FastAPI app, imported by conftest.py at runtime
```

---

## Running Tests

All commands should be run from the repository root (`Testsuite-Dataforge/`).

### Run the full test suite

```bash
pytest backend/
```

### Run a specific high-level directory

```bash
pytest backend/test_apis/
pytest backend/test_libs/
pytest backend/test_internal/
```

### Run a single test file

```bash
pytest backend/test_apis/Integration/test_sensor_data.py
pytest backend/test_libs/Unit_tests/test_payload_decoders_unit.py
```

### Run a single test class

```bash
pytest backend/test_apis/test_sensor_data.py::TestReadingsFilters
```

### Run a single test by name

```bash
pytest backend/test_apis/test_sensor_data.py::TestReadingsFilters::test_filter_by_sensor_euis
```

### Run tests matching a keyword

```bash
pytest -k "sensor"          # all tests with "sensor" in the name
pytest -k "not admin"       # exclude tests with "admin" in the name
```

### Useful flags

| Flag | Effect |
|------|--------|
| `-v` | Verbose output — shows each test name and result |
| `-x` | Stop after the first failure |
| `--tb=short` | Compact traceback (default in CI) |
| `--tb=long` | Full traceback with local variables |
| `--disable-warnings` | Suppress deprecation warnings |
| `-s` | Show print/log output from tests |

Example combining flags:

```bash
pytest backend/test_apis/test_admin_unit.py -v --tb=short -x
```

---