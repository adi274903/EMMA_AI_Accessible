"""
UI styles and custom CSS for the medical AI consultation interface.
"""

from typing import Optional, List, Dict

from accessibility import AccessibilityPrefs, DEFAULT_PREFS, decorative_icon, get_a11y_css
import streamlit as st


def get_custom_css(prefs: Optional[AccessibilityPrefs] = None) -> str:
    """
    Returns the custom CSS for the interface, followed by the accessibility CSS.
    
    Args:
        prefs: Accessibility preferences; None means the defaults.
        
    Returns:
        CSS string to be injected into Streamlit
    """
    base_css = """
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden !important; display: none !important;}
    header {visibility: hidden;}
    
    /* Ensure main content has bottom padding to avoid overlap with fixed nav */
    .main .block-container {
        padding-bottom: 120px !important;
    }
    
    /* Ensure Streamlit app doesn't have overflow issues */
    .stApp {
        background-color: #f5f7fa;
        overflow-x: hidden !important;
    }
    
    /* Ensure body and html don't have overflow that could hide bottom nav */
    body {
        overflow-x: hidden !important;
        padding-bottom: 0 !important;
        margin-bottom: 0 !important;
    }
    
    html {
        overflow-x: hidden !important;
    }
    
    /* Header */
    .podcast-header {
        text-align: right;
        padding: 20px;
        color: #0ea5e9;
        font-weight: 600;
        font-size: 16px;
    }
    
    /* Welcome section */
    .welcome-container {
        text-align: center;
        padding: 80px 20px 40px 20px;
    }
    
    .icon-circle {
        width: 80px;
        height: 80px;
        background: linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 30px auto;
        font-size: 40px;
    }
    
    .greeting {
        font-size: 22px;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 15px;
    }
    
    .question-prompt {
        font-size: 16px;
        color: #64748b;
        line-height: 1.6;
    }
    
    /* Loading screen */
    .loading-container {
        text-align: center;
        padding: 150px 20px;
    }
    
    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 4px solid #e0f2fe;
        border-top: 4px solid #0ea5e9;
        border-radius: 50%;
        margin: 0 auto 30px auto;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-text {
        font-size: 18px;
        color: #64748b;
        margin-top: 20px;
    }
    
    /* Inside get_custom_css() in ui_components.py */
    
    /* Input area - UPDATED */
    .input-container {
        position: fixed;
        bottom: 60px; /* Moved up to clear the bottom nav */
        left: 0;
        right: 0;
        background: white;
        padding: 20px;
        z-index: 1000; /* Force it to be on top of everything else */
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    
    /* Bottom navigation - UPDATED */
    .bottom-nav {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100vw !important;
        max-width: 100% !important;
        background: white !important;
        border-top: none !important;
        display: flex !important;
        justify-content: space-around;
        align-items: center;
        padding: 12px 0 !important;
        z-index: 99999 !important; /* Very high z-index to ensure visibility */
        height: 60px !important;
        min-height: 60px !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        margin: 0 !important;
        box-sizing: border-box !important;
    }
    
    /* Ensure nav items are properly displayed */
    .bottom-nav .nav-item {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .nav-item {
        text-align: center;
        color: #64748b;
        font-size: 14px;
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 0; /* Prevent flex item from overflowing */
    }
    
    .nav-item.active {
        color: #3b82f6;
    }
    
    /* Override any Streamlit container styles that might affect bottom nav */
    [data-testid="stAppViewContainer"] {
        padding-bottom: 0 !important;
    }
    
    /* Ensure bottom nav is not clipped by parent containers */
    .bottom-nav {
        transform: translateZ(0); /* Force hardware acceleration */
        will-change: transform;
    }
    
    .citation-box {
        margin-top: 15px;
        padding-top: 10px;
        border-top: 1px solid #e2e8f0;
        font-size: 12px;
        color: #94a3b8;
    }
    
    .references-box {
        margin-top: 20px;
        padding: 15px;
        background-color: #f8fafc;
        border-left: 4px solid #0ea5e9;
        border-radius: 4px;
    }
    
    .references-title {
        font-size: 14px;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 10px;
    }
    
    .reference-item {
        font-size: 13px;
        color: #475569;
        margin-bottom: 6px;
        padding-left: 8px;
    }
    
    .reference-item:last-child {
        margin-bottom: 0;
    }
</style>
"""
    return base_css + "\n" + get_a11y_css(prefs if prefs is not None else DEFAULT_PREFS)


def get_welcome_screen(doctor_name: str = "Clinician") -> str:
    """
    Returns the HTML for the welcome screen.
    
    Args:
        doctor_name: Name of the clinician to display
        
    Returns:
        HTML string for welcome screen
    """
    return f"""
    <div class="welcome-container">
        <div class="icon-circle" aria-hidden="true">🎧</div>
        <div class="greeting">Hi {doctor_name},</div>
        <div class="question-prompt">
            What clinical question do you want to explore from your<br>last shift?
        </div>
    </div>
    """


def get_loading_screen() -> str:
    """
    Returns the HTML for the loading screen.
    
    Returns:
        HTML string for loading screen
    """
    return """
    <div class="loading-container">
        <div class="loading-spinner"></div>
        <div class="greeting">Loading AI Models...</div>
        <div class="loading-text">This may take a minute ☕</div>
    </div>
    """


def get_header(app_name: str = "EMMA AI") -> str:
    """
    Returns the HTML for the header.
    
    Args:
        app_name: Name of the application
        
    Returns:
        HTML string for header
    """
    return f'<div class="podcast-header">{app_name}</div>'


def get_user_message_html(message: str) -> str:
    """
    Returns formatted HTML for a user message.
    
    Args:
        message: The user's message content
        
    Returns:
        HTML string for user message
    """
    return f"""
    <div class="response-container">
        <div style="color: #64748b; font-size: 14px; margin-bottom: 8px;">You asked:</div>
        <div style="color: #1e293b; font-size: 16px;">{message}</div>
    </div>
    """


def get_assistant_message_html(
    message: str,
    streaming: bool = False,
    citation: Optional[str] = None,
) -> str:
    """
    Returns formatted HTML for an assistant message.

    Args:
        message: The assistant's message content
        streaming: Whether to show the streaming cursor
        citation: Optional citation string to display

    Returns:
        HTML string for assistant message
    """
    cursor = "▌" if streaming else ""
    citation_html = ""

    # Only render citation if not streaming and citation is provided
    if not streaming and citation:
        citation_html = f'<div class="citation-box">{citation}</div>'

    # Visual indicator / header text
    if not streaming:
        audio_icon_html = f"""
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <div style="color: #0ea5e9; font-size: 14px;">{decorative_icon("🩺")} Clinical Response:</div>
        </div>
        """
    else:
        audio_icon_html = f'<div style="color: #0ea5e9; font-size: 14px; margin-bottom: 8px;">{decorative_icon("🩺")} Clinical Response:</div>'

    return f"""
    <div class="response-container">
        {audio_icon_html}
        <div style="color: #1e293b; font-size: 15px; line-height: 1.6;">{message}{cursor}</div>
        {citation_html}
    </div>
    """


def get_references_html(references: List[Dict[str, str]]) -> str:
    """
    Returns formatted HTML for references section (textbook + page).
    
    Args:
        references: List of dicts with 'textbook' and 'page' keys
        
    Returns:
        HTML string for references section
    """
    if not references:
        return ""
    
    reference_items = []
    for ref in references:
        textbook = ref.get('textbook', 'Unknown')
        page = ref.get('page', 'N/A')
        reference_items.append(
            f'<div class="reference-item">{decorative_icon("📖")} {textbook} - Page {page}</div>'
        )
    
    references_html = "\n".join(reference_items)
    
    return f"""
    <div class="references-box">
        <div class="references-title">{decorative_icon("📚")} References</div>
        {references_html}
    </div>
    """


def get_bottom_nav() -> str:
    """
    Returns the HTML for the bottom navigation bar.
    
    Returns:
        HTML string for bottom navigation
    """
    return """
    <div class="bottom-nav" style="position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important; width: 100% !important; z-index: 99999 !important; background: white !important; display: flex !important; justify-content: space-around !important; align-items: center !important; padding: 12px 0 !important; height: 60px !important; box-shadow: 0 -2px 10px rgba(0,0,0,0.1) !important; margin: 0 !important; box-sizing: border-box !important; border-top: none !important;">
        <div class="nav-item active" style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <div style="font-size: 20px; margin-bottom: 4px;" aria-hidden="true">💬</div>
            <div style="font-size: 14px;">Ask AI</div>
        </div>
        <div class="nav-item" style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <div style="font-size: 20px; margin-bottom: 4px;" aria-hidden="true">📚</div>
            <div style="font-size: 14px;">Podcast Library</div>
        </div>
    </div>
    """


def get_bottom_spacing() -> str:
    """
    Returns HTML for spacing at the bottom to account for fixed navigation.
    
    Returns:
        HTML string for bottom spacing
    """
    return '<div style="height: 100px; margin-bottom: 20px;"></div>'

def display_assistant_audio(
    audio_data: Optional[bytes],
    autoplay: bool = False,
    transcript: Optional[str] = None,
) -> None:
    """
    Display the generated audio with Streamlit's audio component.

    Args:
        audio_data: WAV bytes from the backend, or None.
        autoplay: Start playback immediately. Off by default: unexpected sound is a
            WCAG 1.4.2 problem, so playing is an explicit user choice.
        transcript: Optional caption rendered above the player. The caption is what makes
            the audio optional rather than the only way to get the answer.
    """
    if not audio_data:
        return
    if transcript:
        st.caption(transcript)
    # The backend speaks WAV (see MedicalAIBackend._pcm_to_wav).
    st.audio(audio_data, format="audio/wav", autoplay=autoplay)
