"""Unit tests for accessibility.py (pure Python: no Streamlit, no models, no network)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import accessibility as a11y  # noqa: E402


def test_defaults_are_conservative():
    prefs = a11y.DEFAULT_PREFS
    assert prefs.font_scale == 1.0
    assert prefs.high_contrast is False
    assert prefs.reduced_motion is False
    # Unexpected sound is disorienting: autoplay must be off unless asked for.
    assert prefs.autoplay_audio is False


@pytest.mark.parametrize(
    "raw,expected",
    [(1.0, 1.0), (1.15, 1.15), (0.5, 1.0), (9.0, 1.5), ("1.3", 1.3), (None, 1.0), ("x", 1.0)],
)
def test_clamp_font_scale(raw, expected):
    assert a11y.clamp_font_scale(raw) == expected


def test_prefs_from_mapping_is_tolerant():
    assert a11y.prefs_from_mapping(None) == a11y.DEFAULT_PREFS
    assert a11y.prefs_from_mapping({}) == a11y.DEFAULT_PREFS

    prefs = a11y.prefs_from_mapping(
        {"font_scale": 3.0, "high_contrast": 1, "reduced_motion": "yes", "unknown": 42}
    )
    assert prefs.font_scale == 1.5
    assert prefs.high_contrast is True
    assert prefs.reduced_motion is True
    assert prefs.autoplay_audio is False


def test_css_always_has_focus_targets_and_sr_only():
    css = a11y.get_a11y_css(a11y.DEFAULT_PREFS)
    assert css.startswith("<style>") and css.endswith("</style>")
    assert ":focus-visible" in css
    assert f"{a11y.MIN_TARGET_PX}px" in css
    assert ".sr-only" in css
    assert "prefers-reduced-motion" in css
    assert "prefers-contrast: more" in css


def test_css_scales_font():
    small = a11y.get_a11y_css(a11y.AccessibilityPrefs(font_scale=1.0))
    large = a11y.get_a11y_css(a11y.AccessibilityPrefs(font_scale=1.3))
    assert "font-size: 16.0px" in small
    assert "font-size: 20.8px" in large
    assert small != large


def test_css_forces_motion_and_contrast_only_when_requested():
    plain = a11y.get_a11y_css(a11y.DEFAULT_PREFS)
    assert "user forced reduced motion" not in plain
    assert "user forced high contrast" not in plain

    forced = a11y.get_a11y_css(
        a11y.AccessibilityPrefs(reduced_motion=True, high_contrast=True)
    )
    assert "user forced reduced motion" in forced
    assert "user forced high contrast" in forced
    assert "#0b1220" in forced


def test_button_label_never_empty_and_requires_text():
    assert a11y.button_label("Listen") == "Listen"
    assert a11y.button_label("Listen", "🔊") == "🔊 Listen"
    assert a11y.button_label("  Listen  ", "") == "Listen"
    with pytest.raises(ValueError):
        a11y.button_label("   ")


def test_decorative_icon_is_hidden_from_assistive_tech():
    assert a11y.decorative_icon("🩺") == '<span aria-hidden="true">🩺</span>'


def test_audio_labels_differ_by_mode():
    assert "verbatim" in a11y.audio_label("full")
    assert "rewritten" in a11y.audio_label("summary")


def test_describe_audio_prefixes_and_truncates():
    short = a11y.describe_audio("Short answer.", mode="full")
    assert short.startswith("Spoken verbatim:")
    assert "Short answer." in short

    long_text = " ".join(["word"] * 200)
    caption = a11y.describe_audio(long_text, mode="summary", max_chars=60)
    assert caption.startswith("Spoken summary:")
    assert "…" in caption
    assert len(caption) <= len("Spoken summary: ") + 60 + 1

    assert a11y.describe_audio("", mode="summary") == "Spoken summary: (no text)"


def test_describe_audio_collapses_whitespace():
    caption = a11y.describe_audio("line one\n\nline   two", mode="summary")
    assert "\n" not in caption
    assert "line one line two" in caption
