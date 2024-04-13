#!/bin/bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -U pip
pip3 install -Ur ./Python/requirements.txt
