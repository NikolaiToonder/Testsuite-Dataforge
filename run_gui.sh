#!/bin/bash
# Simple launcher for the Test Runner GUI

cd "$(dirname "$0")" || exit
python3 test_runner_gui.py
