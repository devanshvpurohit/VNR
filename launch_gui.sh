#!/bin/bash

# SURDAS GUI Launcher Script
# Launches the PyQt5 desktop application

echo "🛡️  SURDAS - Assistive Vision System"
echo "======================================"
echo ""
echo "Starting PyQt5 GUI application..."
echo ""

# Check if PyQt5 is installed
python3 -c "import PyQt5" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ PyQt5 not found. Installing dependencies..."
    pip3 install PyQt5>=5.15.0
    echo ""
fi

# Launch GUI
python3 surdas_gui.py

echo ""
echo "GUI application closed."
