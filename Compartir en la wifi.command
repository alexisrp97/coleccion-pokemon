#!/bin/bash
cd "$(dirname "$0")"
echo "Arrancando la vitrina compartida…"
python3 tcg.py serve
