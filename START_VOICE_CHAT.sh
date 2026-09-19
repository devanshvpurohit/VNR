#!/bin/bash
# Quick start script for SURDAS Voice Chat

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          🎤 SURDAS VOICE CHAT WITH OLLAMA                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running!"
    echo ""
    echo "Please start Ollama first:"
    echo "  Option 1: ollama serve"
    echo "  Option 2: brew services start ollama"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✓ Ollama is running"
echo ""
echo "Starting voice chat..."
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  HOW TO USE:                                                │"
echo "│  • No wake word needed - just speak!                        │"
echo "│  • System detects when you stop talking                     │"
echo "│  • Ollama responds and speaks the answer                    │"
echo "│  • Ready for your next question immediately                 │"
echo "│  • Press Ctrl+C to exit                                     │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "Press Enter to start..."
read

python3 simple_voice_assistant.py
