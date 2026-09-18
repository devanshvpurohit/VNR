#!/bin/bash

# SURDAS GUI Launcher Script
# Launches the Tkinter desktop application

echo "🛡️  SURDAS - Assistive Vision System"
echo "======================================"
echo ""
echo "Starting Tkinter GUI application..."
echo ""

# Check if Pillow is installed
python3 -c "import PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Pillow (PIL) not found. Installing dependencies..."
    pip3 install Pillow>=10.0.0
    echo ""
fi

# Launch GUI
python3 surdas_brain.py --gui

echo ""
echo "GUI application closed."
