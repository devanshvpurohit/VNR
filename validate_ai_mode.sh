#!/bin/bash
# AI Voice Mode Validation Script
# Checks all components before launch

echo "🔍 AI Voice Mode - Pre-Flight Validation"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Check Python version
echo -n "Checking Python version... "
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ $(echo "$PYTHON_VERSION 3.8" | awk '{print ($1 >= $2)}') -eq 1 ]]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (need >= 3.8)"
    ERRORS=$((ERRORS + 1))
fi

# Check required Python packages
echo ""
echo "Checking Python dependencies:"

check_package() {
    PACKAGE=$1
    IMPORT_NAME=${2:-$1}
    echo -n "  - $PACKAGE... "
    if python3 -c "import $IMPORT_NAME" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC} (run: pip3 install $PACKAGE)"
        ERRORS=$((ERRORS + 1))
    fi
}

check_package "pyaudio" "pyaudio"
check_package "numpy" "numpy"
check_package "whisper" "whisper"
check_package "pyttsx3" "pyttsx3"
check_package "requests" "requests"
check_package "pynput" "pynput"

# Check Ollama
echo ""
echo -n "Checking Ollama service... "
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Running"
    
    # Check if llama3.2 model exists
    echo -n "Checking Ollama model (llama3.2)... "
    if curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
        echo -e "${GREEN}✓${NC} Installed"
    else
        echo -e "${YELLOW}⚠${NC} Not found (run: ollama pull llama3.2)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${RED}✗${NC} Not running (run: ollama serve)"
    ERRORS=$((ERRORS + 1))
fi

# Check microphone access
echo ""
echo -n "Checking microphone access... "
if python3 -c "import pyaudio; p=pyaudio.PyAudio(); p.get_default_input_device_info(); p.terminate()" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Accessible"
else
    echo -e "${RED}✗${NC} No microphone detected"
    ERRORS=$((ERRORS + 1))
fi

# Check required files
echo ""
echo "Checking required files:"

check_file() {
    FILE=$1
    echo -n "  - $FILE... "
    if [ -f "$FILE" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC} Missing"
        ERRORS=$((ERRORS + 1))
    fi
}

check_file "surdas_brain.py"
check_file "simple_voice_assistant.py"
check_file "workers.py"
check_file "test_ai_mode.py"

# Run unit tests
echo ""
echo -n "Running unit tests... "
if python3 test_ai_mode.py >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} All tests passed"
else
    echo -e "${RED}✗${NC} Tests failed (run: python3 test_ai_mode.py)"
    ERRORS=$((ERRORS + 1))
fi

# Check worker methods
echo ""
echo -n "Checking worker pause/resume methods... "
if python3 -c "from workers import VisionWorker, SafetyWorker; from unittest.mock import Mock; m=Mock(); m.stream=Mock(); m.stream.get_frame=Mock(return_value=None); v=VisionWorker(m); s=SafetyWorker(m,v); assert hasattr(v,'pause') and hasattr(v,'resume') and hasattr(s,'pause') and hasattr(s,'resume')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Present"
else
    echo -e "${RED}✗${NC} Missing"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "========================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "🚀 AI Voice Mode is ready to use!"
    echo ""
    echo "Quick start:"
    echo "  python3 surdas_brain.py"
    echo "  Press 'A' to activate AI Voice Mode"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS WARNING(S)${NC}"
    echo "System should work but some features may be limited."
    echo ""
    exit 0
else
    echo -e "${RED}✗ $ERRORS ERROR(S), $WARNINGS WARNING(S)${NC}"
    echo "Please fix the errors above before using AI Voice Mode."
    echo ""
    exit 1
fi
