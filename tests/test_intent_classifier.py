"""
tests/test_intent_classifier.py

Tests for intent classification — rule-based fallback paths.
"""
import pytest
from backend.orchestrator.intent_classifier import IntentClassifier


@pytest.fixture
def classifier():
    return IntentClassifier()


def test_rule_based_book_en(classifier):
    result = classifier._rule_based("I want to book an appointment with Dr. Sharma")
    assert result.label == "book"
    assert result.confidence >= 0.7


def test_rule_based_book_hi(classifier):
    result = classifier._rule_based("mujhe appointment chahiye")
    assert result.label == "book"


def test_rule_based_cancel(classifier):
    result = classifier._rule_based("please cancel my appointment")
    assert result.label == "cancel"


def test_rule_based_greeting(classifier):
    result = classifier._rule_based("hello, namaste")
    assert result.label == "greeting"
    assert result.confidence >= 0.9


def test_rule_based_fallback(classifier):
    result = classifier._rule_based("what is the weather today")
    assert result.label == "other"
