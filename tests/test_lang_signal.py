"""
tests/test_lang_signal.py

Tests for language switch detection.
"""
import pytest
from backend.stt_service.lang_signal import detect_lang_switch, normalize_lang


def test_detect_switch_to_hindi():
    signal = detect_lang_switch("hindi mein baat karo please", current_lang="en")
    assert signal is not None
    assert signal.lang == "hi"
    assert signal.confidence == 0.99


def test_detect_switch_to_english():
    signal = detect_lang_switch("please speak in english", current_lang="hi")
    assert signal is not None
    assert signal.lang == "en"


def test_no_switch_same_lang():
    signal = detect_lang_switch("mujhe appointment chahiye", current_lang="hi")
    assert signal is None


def test_normalize_lang_codes():
    assert normalize_lang("en-IN") == "en"
    assert normalize_lang("hi-IN") == "hi"
    assert normalize_lang("ta-IN") == "ta"
    assert normalize_lang("unknown") == "en"  # default
