"""
i18n_phrases.py — Bilingual (English + Hindi) phrase dictionary for SURDAS.

Every intent has an "en" list and a "hi" list.
`match(intent_dict, text)` checks both language lists against the text,
returning True on any hit.  Callers never need to know which language
the STT returned — this module handles both transparently.

Usage:
    from voice.i18n_phrases import match, WAKE_WORDS, TORCH_ON, ...

    if match(TORCH_ON, text):
        ...
"""
from __future__ import annotations
from typing import Dict, List


# ── Type alias ────────────────────────────────────────────────────────────────
IntentDict = Dict[str, List[str]]


# ── Core match helper ─────────────────────────────────────────────────────────

def match(intent_dict: IntentDict, text: str) -> bool:
    """
    Return True if *text* contains any phrase from *intent_dict*
    (checked across both 'en' and 'hi' keys).

    Comparison is case-insensitive for Latin script; Devanagari is
    matched as-is (no case concept), so STT output must not be
    unnecessarily modified before calling this.
    """
    lower = text.lower()
    for lang, phrases in intent_dict.items():
        for phrase in phrases:
            # Latin phrases: lowercase compare.  Devanagari: direct compare.
            needle = phrase.lower() if lang == "en" else phrase
            haystack = lower if lang == "en" else text
            if needle in haystack:
                return True
    return False


# ── Phrase dictionaries ───────────────────────────────────────────────────────

WAKE_WORDS: IntentDict = {
    "en": [
        "hey surdas", "surdas", "hey assistant",
        "surdas assistant", "hey surda", "soordas", "hey soordas", "sura das",
    ],
    "hi": [
        "हे सुरदास", "सुरदास", "सूरदास",
        "अरे सुरदास", "ए सुरदास",
    ],
}

NAV_MODE: IntentDict = {
    "en": [
        "navigation mode", "nav mode",
        "resume navigation", "go to navigation",
        "rasta dikhao", "rasta batao", "navigation shuru karo",
    ],
    "hi": [
        "नेविगेशन मोड", "नेविगेशन शुरू करो",
        "रास्ता दिखाओ", "रास्ता बताओ",
    ],
}

NAV_NAVIGATE_TO: IntentDict = {
    "en": [
        "navigate to", "take me to", "directions to", "how to go to",
        "start walking to", "start navigation to", "where is",
    ],
    "hi": [
        "तक ले चलो", "के लिए नेविगेशन शुरू करो", "का रास्ता बताओ",
        "कहाँ है", "किधर है",
    ],
}

NAV_STOP: IntentDict = {
    "en": [
        "stop navigation", "cancel navigation", "end navigation",
        "stop walking navigation",
    ],
    "hi": [
        "नेविगेशन बंद करो", "नेविगेशन रोको",
    ],
}

NAV_REPEAT: IntentDict = {
    "en": [
        "repeat directions", "say again", "repeat instruction",
        "what was that",
    ],
    "hi": [
        "दिशा दोहराओ", "फिर से कहो", "दोहराओ",
    ],
}

NAV_WHERE_AM_I: IntentDict = {
    "en": [
        "where am i", "current location", "where are we",
    ],
    "hi": [
        "मैं कहाँ हूँ", "हम कहाँ हैं",
    ],
}

NAV_NEAREST: IntentDict = {
    "en": [
        "find nearest", "nearest", "where is the closest", "closest",
    ],
    "hi": [
        "नजदीकी खोजो", "नज़दीकी", "सबसे पास",
    ],
}

OCR_MODE: IntentDict = {
    "en": [
        "read text", "read this", "read sign", "read document",
        "scan text", "ocr mode", "start reading", "what does it say",
        "text padho", "yeh padho", "kya likha hai", "padh ke batao",
    ],
    "hi": [
        "टेक्स्ट पढ़ो", "यह पढ़ो", "पाठ पढ़ो", "स्कैन करो",
        "क्या लिखा है", "पढ़कर बताओ", "बोर्ड पढ़ो",
    ],
}

TORCH_ON: IntentDict = {
    "en": [
        "turn on light", "turn on torch", "light on", "torch on",
        "flash on", "flashlight on", "turn on flashlight",
        "light jalao", "light on karo", "torch on karo", "roshni karo", "roshni jalao",
    ],
    "hi": [
        "टॉर्च ऑन करो", "लाइट जलाओ", "रोशनी करो",
        "टॉर्च चालू करो", "लाइट चालू करो", "फ्लैश चालू करो",
        "रोशनी जलाओ",
    ],
}

TORCH_OFF: IntentDict = {
    "en": [
        "turn off light", "turn off torch", "light off", "torch off",
        "flash off", "flashlight off", "turn off flashlight",
    ],
    "hi": [
        "टॉर्च ऑफ करो", "लाइट बंद करो", "रोशनी बंद करो",
        "टॉर्च बंद करो", "फ्लैश बंद करो",
    ],
}

STOP_SILENCE: IntentDict = {
    "en": [
        "stop", "quiet", "silence", "be quiet", "shut up", "cancel",
    ],
    "hi": [
        "रुको", "चुप रहो", "बंद करो", "शांत रहो", "मत बोलो",
    ],
}

STATUS: IntentDict = {
    "en": [
        "system status", "connection status", "your status", "status report",
    ],
    "hi": [
        "स्थिति बताओ", "सिस्टम स्टेटस", "क्या हाल है",
    ],
}

TIME_QUERY: IntentDict = {
    "en": [
        "what time", "what's the time", "whats the time",
        "what is the time", "tell me the time", "current time",
        "time now", "time please", "time right now",
    ],
    "hi": [
        "समय बताओ", "क्या समय हुआ", "अभी क्या बजे हैं",
        "कितने बजे हैं", "टाइम बताओ",
    ],
}

DATE_QUERY: IntentDict = {
    "en": [
        "what date", "what's the date", "whats the date",
        "what day", "today's date", "todays date",
        "what is today", "tell me the date",
    ],
    "hi": [
        "आज की तारीख", "तारीख बताओ", "आज क्या दिन है",
        "आज कौन सा दिन है", "डेट बताओ",
    ],
}

VOLUME_UP: IntentDict = {
    "en": ["volume up", "increase volume", "louder"],
    "hi": [
        "आवाज़ बढ़ाओ", "वॉल्यूम बढ़ाओ", "ज़ोर से बोलो",
    ],
}

VOLUME_DOWN: IntentDict = {
    "en": ["volume down", "decrease volume", "quieter", "lower volume"],
    "hi": [
        "आवाज़ कम करो", "वॉल्यूम कम करो", "धीरे बोलो",
    ],
}

VOLUME_MUTE: IntentDict = {
    "en": ["mute volume", "mute sound"],
    "hi": [
        "म्यूट करो", "आवाज़ बंद करो", "चुप हो जाओ",
    ],
}

SCREENSHOT: IntentDict = {
    "en": ["screenshot", "take a screenshot", "capture screen"],
    "hi": [
        "स्क्रीनशॉट लो", "स्क्रीन कैप्चर करो",
    ],
}

LOCK_SCREEN: IntentDict = {
    "en": ["lock screen", "lock my mac", "lock computer"],
    "hi": [
        "स्क्रीन लॉक करो", "कंप्यूटर लॉक करो",
    ],
}

# App commands — triggers only; app name is extracted separately.
APP_OPEN: IntentDict = {
    "en": [
        "open ", "launch ", "start ", "run ",
        "open up ", "open the ", "launch the ", "can you open ",
    ],
    "hi": [
        "खोलो ", "खोल दो ", "चालू करो ",
        "शुरू करो ",
    ],
}

APP_CLOSE: IntentDict = {
    "en": ["close ", "quit ", "exit ", "kill ", "close the ", "quit the "],
    "hi": [
        "बंद करो ", "बंद कर दो ", "बंद कर ",
    ],
}

APP_LIST: IntentDict = {
    "en": ["what apps", "which apps", "list apps", "what can you open", "supported apps"],
    "hi": [
        "कौन से ऐप", "ऐप लिस्ट", "कौन से एप्लीकेशन",
    ],
}

WHAT_DO_YOU_SEE: IntentDict = {
    "en": [
        "what do you see", "what is in front", "describe surroundings",
        "describe scene", "any obstacles", "is path clear", "am i safe",
    ],
    "hi": [
        "क्या देख रहे हो", "सामने क्या है", "रास्ता साफ है",
        "कोई रुकावट है", "आगे क्या है", "बताओ क्या दिख रहा है",
    ],
}

MODEL_LIST: IntentDict = {
    "en": [
        "list models", "available models", "what models",
        "which models", "show models", "installed models",
    ],
    "hi": [
        "मॉडल लिस्ट", "कौन से मॉडल हैं", "मॉडल बताओ",
    ],
}

MODEL_CURRENT: IntentDict = {
    "en": [
        "what model", "current model", "which model",
        "what ai model", "which ai",
    ],
    "hi": [
        "कौन सा मॉडल", "वर्तमान मॉडल", "अभी कौन सा मॉडल",
    ],
}

# Language switch commands
LANG_SWITCH_HINDI: IntentDict = {
    "en": [
        "speak in hindi", "switch to hindi", "talk in hindi",
        "hindi please",
    ],
    "hi": [
        "हिंदी में बात करो", "हिंदी में बोलो", "हिन्दी में बोलो",
    ],
}

LANG_SWITCH_ENGLISH: IntentDict = {
    "en": [
        "speak in english", "switch to english", "talk in english",
        "english please",
    ],
    "hi": [
        "अंग्रेज़ी में बोलो", "इंग्लिश में बात करो",
        "अंग्रेजी में बोलो",
    ],
}

# Indoor navigation and spatial memory commands
INDOOR_NAV_TO_OBJECT: IntentDict = {
    "en": [
        "guide me to", "take me to the", "navigate to the",
        "where is the", "find the", "show me the way to",
    ],
    "hi": [
        "मुझे ले चलो", "का रास्ता बताओ", "कहाँ है",
        "तक ले जाओ", "दिखाओ कहाँ है",
    ],
}

INDOOR_NAV_TO_LANDMARK: IntentDict = {
    "en": [
        "guide me to", "take me to", "navigate to",
        "go to", "how to reach", "show me",
    ],
    "hi": [
        "मुझे ले चलो", "का रास्ता बताओ",
        "तक ले जाओ", "कैसे पहुँचे",
    ],
}

ROOM_LABEL: IntentDict = {
    "en": [
        "this is the", "label this room as", "remember this as",
        "this room is", "call this room", "call this the",
        "this is called", "name this room",
    ],
    "hi": [
        "यह है", "इस कमरे का नाम", "इसे याद रखो",
        "यह कमरा है", "इसे कहते हैं",
    ],
}

OBJECT_LABEL: IntentDict = {
    "en": [
        "this is a", "this is the", "label this as",
        "remember this as", "this object is", "call this",
    ],
    "hi": [
        "यह है", "इसे याद रखो", "यह वस्तु है",
        "इसका नाम है",
    ],
}

LANDMARK_LABEL: IntentDict = {
    "en": [
        "remember this location as", "save this spot as",
        "mark this as", "label this spot", "this location is",
    ],
    "hi": [
        "इस जगह को याद रखो", "यह स्थान है",
        "इस स्थान का नाम", "इस जगह को बचाओ",
    ],
}

WHERE_IS_OBJECT: IntentDict = {
    "en": [
        "where is the", "where's the", "find the",
        "locate the", "show me the", "where did i put",
    ],
    "hi": [
        "कहाँ है", "किधर है", "कहाँ रखा है",
        "ढूंढो", "दिखाओ कहाँ है",
    ],
}

WHAT_ROOM: IntentDict = {
    "en": [
        "what room is this", "which room am i in",
        "what is this room", "name this room",
    ],
    "hi": [
        "यह कौन सा कमरा है", "कौन सा कमरा है यह",
        "मैं किस कमरे में हूँ",
    ],
}

LIST_ROOMS: IntentDict = {
    "en": [
        "what rooms do you know", "list rooms", "tell me the rooms",
        "which rooms are saved", "what rooms are there",
    ],
    "hi": [
        "कौन से कमरे हैं", "कमरों की सूची", "कौन से कमरे याद हैं",
    ],
}

LIST_OBJECTS: IntentDict = {
    "en": [
        "what objects do you know", "list objects", "what do you remember",
        "what have you seen", "what objects are saved",
    ],
    "hi": [
        "कौन सी चीज़ें याद हैं", "क्या याद है", "वस्तुओं की सूची",
    ],
}

DESCRIBE_SURROUNDINGS: IntentDict = {
    "en": [
        "describe surroundings", "what's around me", "what is nearby",
        "what objects are near", "tell me what's nearby",
    ],
    "hi": [
        "आसपास क्या है", "पास में क्या है", "आसपास बताओ",
    ],
}

PAUSE_NAVIGATION: IntentDict = {
    "en": [
        "pause navigation", "pause", "hold on", "wait",
        "stop moving", "pause guidance",
    ],
    "hi": [
        "रुको", "नेविगेशन रोको", "ठहरो", "रुक जाओ",
    ],
}

RESUME_NAVIGATION: IntentDict = {
    "en": [
        "resume navigation", "continue navigation", "resume",
        "keep going", "continue", "go on",
    ],
    "hi": [
        "जारी रखो", "नेविगेशन जारी रखो", "आगे बढ़ो", "चलते रहो",
    ],
}

CLEAR_MEMORY: IntentDict = {
    "en": [
        "forget everything", "clear memory", "reset memory",
        "delete all objects", "forget all rooms",
    ],
    "hi": [
        "सब भूल जाओ", "मेमोरी साफ करो", "सब मिटा दो",
    ],
}

# Hindi filler words to strip from app names / commands
HINDI_FILLERS: List[str] = [
    "कृपया", "अभी", "जल्दी", "ज़रा", "जरा", "थोड़ा", "थोड़ी",
    "please", "now", "for me", "quickly", "up",
]
