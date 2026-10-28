"""
Accessibility preferences and helpers for the EMMA AI interface.

This module is deliberately free of Streamlit and of any model/DB import so that it can be
unit-tested without a GPU, a vector store or an API key. Nothing here changes retrieval or
generation behaviour: it only produces CSS, labels and transcript strings.
"""

from dataclasses import dataclass, fields
from typing import Any, Mapping, Optional

# Minimum interactive target size recommended by WCAG 2.2 (2.5.8 Target Size).
MIN_TARGET_PX = 44

# Font scales offered in the Accessibility panel.
FONT_SCALE_CHOICES = (1.0, 1.15, 1.3)

# Focus ring colour chosen for >= 3:1 contrast against both the light background and the
# white message cards used by the interface.
FOCUS_COLOUR = "#1d4ed8"


@dataclass(frozen=True)
class AccessibilityPrefs:
    """
    User-facing accessibility preferences.

    Attributes:
        font_scale: Multiplier applied to the base font size (clamped to 1.0-1.5).
        high_contrast: Force the high-contrast palette instead of relying on the OS setting.
        reduced_motion: Force motion suppression instead of relying on the OS setting.
        autoplay_audio: Start playing generated audio immediately (off by default: unexpected
            sound is disorienting and is discouraged by WCAG 1.4.2).
    """

    font_scale: float = 1.0
    high_contrast: bool = False
    reduced_motion: bool = False
    autoplay_audio: bool = False


DEFAULT_PREFS = AccessibilityPrefs()


def clamp_font_scale(value: Any) -> float:
    """
    Clamp a user-supplied font scale into the supported range.

    Args:
        value: Anything castable to float; non-numeric input yields the default 1.0.

    Returns:
        A float in [1.0, 1.5].
    """
    try:
        scale = float(value)
    except (TypeError, ValueError):
        return 1.0
    if scale != scale:  # NaN
        return 1.0
    return min(max(scale, 1.0), 1.5)


def prefs_from_mapping(mapping: Optional[Mapping[str, Any]]) -> AccessibilityPrefs:
    """
    Build preferences from a loosely-typed mapping (e.g. ``st.session_state``).

    Unknown keys are ignored and missing keys fall back to the defaults, so an outdated
    session state never breaks the page.

    Args:
        mapping: Mapping of preference names to values, or None.

    Returns:
        A normalised AccessibilityPrefs instance.
    """
    if not mapping:
        return DEFAULT_PREFS
    known = {f.name: f.default for f in fields(AccessibilityPrefs)}
    values = {}
    for name, default in known.items():
        raw = mapping.get(name, default)
        if name == "font_scale":
            values[name] = clamp_font_scale(raw)
        else:
            values[name] = bool(raw)
    return AccessibilityPrefs(**values)


def get_a11y_css(prefs: AccessibilityPrefs = DEFAULT_PREFS) -> str:
    """
    Return the CSS block that implements the accessibility preferences.

    The block always contains: a visible focus ring, a minimum 44 px target size, an
    ``sr-only`` utility class, and media queries that honour the operating-system
    reduced-motion and contrast preferences. The user preferences add their rules on top.

    Args:
        prefs: Accessibility preferences.

    Returns:
        A ``<style>`` element as a string, ready for ``st.markdown(..., unsafe_allow_html=True)``.
    """
    scale = clamp_font_scale(getattr(prefs, "font_scale", 1.0))
    base_px = round(16 * scale, 2)
    forced_motion = getattr(prefs, "reduced_motion", False)
    forced_contrast = getattr(prefs, "high_contrast", False)

    motion_rules = """
        *, *::before, *::after {
            animation-duration: 0.001ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.001ms !important;
            scroll-behavior: auto !important;
        }
    """
    contrast_rules = """
        .stApp, .main .block-container {
            background-color: #ffffff !important;
            color: #0b1220 !important;
        }
        .stApp p, .stApp li, .stApp span, .stApp div {
            color: #0b1220 !important;
        }
        .stButton > button, .stFormSubmitButton > button {
            border: 2px solid #0b1220 !important;
            color: #0b1220 !important;
            background-color: #ffffff !important;
        }
        .references-box, .message-bubble, .stAudio {
            border: 2px solid #0b1220 !important;
        }
    """

    parts = [
        "<style>",
        "    /* --- accessibility: focus, targets, screen readers (always on) --- */",
        f"    :focus-visible {{ outline: 3px solid {FOCUS_COLOUR} !important; "
        f"outline-offset: 2px !important; }}",
        f"    .stButton > button, .stFormSubmitButton > button, "
        f"input[type='text'], textarea {{ min-height: {MIN_TARGET_PX}px !important; }}",
        "    .sr-only {",
        "        position: absolute !important;",
        "        width: 1px; height: 1px;",
        "        padding: 0; margin: -1px;",
        "        overflow: hidden;",
        "        clip: rect(0, 0, 0, 0);",
        "        white-space: nowrap;",
        "        border: 0;",
        "    }",
        "    /* --- accessibility: text size --- */",
        f"    html, body, .stApp {{ font-size: {base_px}px !important; }}",
        "    /* --- accessibility: OS-level motion preference --- */",
        "    @media (prefers-reduced-motion: reduce) {",
        motion_rules,
        "    }",
        "    /* --- accessibility: OS-level contrast preference --- */",
        "    @media (prefers-contrast: more) {",
        contrast_rules,
        "    }",
    ]

    if forced_motion:
        parts += ["    /* --- accessibility: user forced reduced motion --- */", motion_rules]
    if forced_contrast:
        parts += ["    /* --- accessibility: user forced high contrast --- */", contrast_rules]

    parts.append("</style>")
    return "\n".join(parts)


def button_label(text: str, icon: str = "") -> str:
    """
    Build a button label that always contains text.

    Icon-only controls are inaccessible to screen readers and to anyone who cannot see the
    glyph, so the emoji is decoration and the text is mandatory.

    Args:
        text: Human-readable action text (required, non-empty).
        icon: Optional leading emoji or symbol.

    Returns:
        ``"<icon> <text>"`` or just the text when no icon is given.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("button_label requires non-empty text")
    clean_icon = (icon or "").strip()
    return f"{clean_icon} {clean_text}".strip()


def decorative_icon(icon: str) -> str:
    """
    Wrap an emoji so assistive technology skips it.

    Args:
        icon: The emoji or symbol.

    Returns:
        An inline ``<span aria-hidden="true">`` element.
    """
    return f'<span aria-hidden="true">{icon}</span>'


def audio_label(mode: str = "summary") -> str:
    """
    Human-readable label describing which audio the user is about to hear.

    Args:
        mode: ``"full"`` for a verbatim read, anything else for the rewritten script.

    Returns:
        The label text.
    """
    if mode == "full":
        return "Audio: verbatim reading of the response"
    return "Audio: script rewritten for listening"


def describe_audio(text: str, mode: str = "summary", max_chars: int = 160) -> str:
    """
    Build the visible transcript caption shown with each audio player.

    The caption is the accessible alternative to audio alone: it tells the user what will be
    spoken and lets them skim without playing anything.

    Args:
        text: The response text that is spoken (or its rewritten script).
        mode: ``"full"`` or ``"summary"``; selects the prefix.
        max_chars: Truncation length for the preview (must be >= 20).

    Returns:
        A single-line caption string.
    """
    limit = max(20, int(max_chars))
    spoken = " ".join((text or "").split())
    if len(spoken) > limit:
        spoken = spoken[: limit - 1].rstrip() + "…"
    prefix = "Spoken verbatim" if mode == "full" else "Spoken summary"
    return f"{prefix}: {spoken}" if spoken else f"{prefix}: (no text)"
