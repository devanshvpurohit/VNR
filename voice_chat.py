#!/usr/bin/env python3
"""
voice_chat.py — Voice chat with Ollama (simplified, always-on)

The EASIEST way to chat with Ollama via voice.
No wake word. No complex detection. Just talk!

Usage:
    python3 voice_chat.py
"""

import sys
import os

# Suppress warnings
import warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

print("\n" + "="*70)
print("  🎤 SURDAS VOICE CHAT")
print("  Talk to Ollama - No wake word needed")
print("="*70 + "\n")

try:
    # Quick check
    print("Checking system...")
    
    from voice.llm import LocalLLM
    llm = LocalLLM()
    
    if not llm.is_available():
        print("✗ Ollama not running!")
        print("\nPlease start Ollama first:")
        print("  ollama serve")
        print("\nOr in a new terminal:")
        print("  brew services start ollama")
        sys.exit(1)
    
    print(f"✓ Ollama ready: {llm.model_name}\n")
    
    # Now run the simple assistant
    print("Starting voice chat...\n")
    os.system("python3 simple_voice_assistant.py")
    
except KeyboardInterrupt:
    print("\n\nGoodbye!")
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Is Ollama running? (ollama serve)")
    print("  2. Is microphone working? (System Preferences → Security)")
    print("  3. Run basic test: python3 test_basic_voice.py")
    sys.exit(1)
