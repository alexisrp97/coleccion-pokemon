#!/bin/bash
# Doble clic aquí para abrir collector.app. Si macOS avisa de que no se puede
# abrir, haz clic derecho sobre este fichero y elige "Abrir".
cd "$(dirname "$0")"
echo "Arrancando collector.app…"
python3 tcg.py
