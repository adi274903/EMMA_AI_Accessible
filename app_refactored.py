"""
Main Streamlit application for medical AI consultation.
This is a refactored, modular version that separates concerns.
"""

import streamlit as st
from accessibility import (
    DEFAULT_PREFS,
    FONT_SCALE_CHOICES,
    AccessibilityPrefs,
    button_label,
    describe_audio,
    prefs_from_mapping,
)
from backend import MedicalAIBackend
from ui_components import (
    display_assistant_audio,
    get_assistant_message_html,
    get_bottom_nav,
    get_bottom_spacing,
    get_custom_css,
    get_header,
    get_loading_screen,
    get_references_html,
    get_user_message_html,
    get_welcome_screen,
)
from config import get_default_config
from session_state import SessionState


def configure_page(config):
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=config.ui.page_title,
        page_icon=config.ui.page_icon,
        layout=config.ui.layout,
        initial_sidebar_state=config.ui.initial_sidebar_state
    )


# Session-state keys for the accessibility controls.
A11Y_FONT_SCALE_KEY = "a11y_font_scale"
A11Y_HIGH_CONTRAST_KEY = "a11y_high_contrast"
A11Y_REDUCED_MOTION_KEY = "a11y_reduced_motion"
A11Y_AUTOPLAY_KEY = "a11y_autoplay_audio"

FONT_SCALE_LABELS = {1.0: "Default", 1.15: "Large", 1.3: "Extra large"}


def get_a11y_prefs() -> AccessibilityPrefs:
    """
    Read the accessibility preferences from session state.

    Returns:
        Normalised preferences; defaults are used for anything missing or invalid.
    """
    return prefs_from_mapping(
        {
            "font_scale": st.session_state.get(A11Y_FONT_SCALE_KEY, DEFAULT_PREFS.font_scale),
            "high_contrast": st.session_state.get(A11Y_HIGH_CONTRAST_KEY, DEFAULT_PREFS.high_contrast),
            "reduced_motion": st.session_state.get(A11Y_REDUCED_MOTION_KEY, DEFAULT_PREFS.reduced_motion),
            "autoplay_audio": st.session_state.get(A11Y_AUTOPLAY_KEY, DEFAULT_PREFS.autoplay_audio),
        }
    )


def render_accessibility_panel() -> AccessibilityPrefs:
    """
    Render the sidebar accessibility controls.

    Every control maps to a preference that only changes presentation: text size, contrast,
    motion and whether generated audio starts on its own.

    Returns:
        The preferences after the user's changes.
    """
    for key, default in (
        (A11Y_FONT_SCALE_KEY, DEFAULT_PREFS.font_scale),
        (A11Y_HIGH_CONTRAST_KEY, DEFAULT_PREFS.high_contrast),
        (A11Y_REDUCED_MOTION_KEY, DEFAULT_PREFS.reduced_motion),
        (A11Y_AUTOPLAY_KEY, DEFAULT_PREFS.autoplay_audio),
    ):
        st.session_state.setdefault(key, default)

    with st.sidebar:
        with st.expander("Accessibility", expanded=False):
            st.radio(
                "Text size",
                options=list(FONT_SCALE_CHOICES),
                format_func=lambda scale: FONT_SCALE_LABELS.get(scale, "Custom"),
                key=A11Y_FONT_SCALE_KEY,
                horizontal=True,
            )
            st.checkbox(
                "High contrast",
                key=A11Y_HIGH_CONTRAST_KEY,
                help="Force the high-contrast palette instead of relying on your system setting.",
            )
            st.checkbox(
                "Reduce motion",
                key=A11Y_REDUCED_MOTION_KEY,
                help="Stop animations and smooth scrolling.",
            )
            st.checkbox(
                "Play audio automatically",
                key=A11Y_AUTOPLAY_KEY,
                help="Off by default. When on, generated audio starts playing as soon as it is ready.",
            )

    return get_a11y_prefs()


def inject_custom_css(prefs: AccessibilityPrefs = DEFAULT_PREFS) -> None:
    """Inject the base CSS followed by the accessibility CSS for the given preferences."""
    st.markdown(get_custom_css(prefs), unsafe_allow_html=True)


@st.cache_resource
def initialize_backend(config) -> MedicalAIBackend:
    """
    Initialize and load the backend models.
    This is cached to ensure models are only loaded once.
    
    Args:
        config: Application configuration
        
    Returns:
        Initialized MedicalAIBackend instance
    """
    backend = MedicalAIBackend(
        vectorstore_path=config.model.vectorstore_path,
        tts_model_name=config.model.tts_model_name,
        tts_voice_name=config.model.tts_voice_name
    )
    backend.load_models()
    return backend


def render_loading_screen(config):
    """Render the loading screen while models initialize."""
    st.markdown(get_header(config.ui.app_name), unsafe_allow_html=True)
    st.markdown(get_loading_screen(), unsafe_allow_html=True)


def render_welcome_screen(config):
    """Render the welcome screen when no messages exist."""
    st.markdown(
        get_welcome_screen(config.ui.doctor_name), 
        unsafe_allow_html=True
    )


def generate_audio_with_progress(backend, text: str, message_index: int, use_summary: bool = True):
    """
    Generate audio with an animated progress bar.
    """
    import time
    import threading
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    result = {"audio": None, "error": None, "done": False}
    
    def do_tts():
        try:
            # UPDATED: changed 'summarize' to 'use_summary' to match backend
            result["audio"] = backend.generate_speech(text, use_summary=use_summary)
        except Exception as e:
            result["error"] = str(e)
        finally:
            result["done"] = True
    
    thread = threading.Thread(target=do_tts)
    thread.start()
    
    # ... (Rest of the animation logic stays exactly the same) ...
    
    # Animate progress bar while waiting
    progress = 0
    stages = [
        (0.1, "🎙️ Connecting to TTS service..."),
        (0.25, "📝 Processing text..."),
        (0.4, "🔊 Generating audio..."),
        (0.6, "🎵 Synthesizing speech..."),
        (0.8, "📦 Finalizing audio..."),
    ]
    stage_index = 0
    
    while not result["done"]:
        if stage_index < len(stages) and progress >= stages[stage_index][0]:
            status_text.markdown(f"*{stages[stage_index][1]}*")
            stage_index += 1
        
        if progress < 0.9:
            increment = 0.02 if progress < 0.5 else 0.01
            progress = min(progress + increment, 0.9)
            progress_bar.progress(progress)
        
        time.sleep(0.1)
    
    thread.join()
    
    if result["audio"]:
        status_text.markdown("*✅ Audio ready!*")
        progress_bar.progress(1.0)
        time.sleep(0.3)
        status_text.empty()
        progress_bar.empty()
        return result["audio"]
    else:
        status_text.empty()
        progress_bar.empty()
        error_msg = result["error"] or "Unknown error"
        st.error(f"❌ Failed to generate audio: {error_msg}")
        return None

def render_conversation():
    """Render the conversation history with manual TTS buttons."""
    messages = SessionState.get_messages()
    backend = SessionState.get_backend()
    
    for i, message in enumerate(messages):
        if message["role"] == "user":
            st.markdown(
                get_user_message_html(message["content"]), 
                unsafe_allow_html=True
            )
        else:
            # Render the text response
            citation = message.get("citation")
            # Use streaming=True to avoid HTML rendering issues with the "Play Audio" button
            st.markdown(
                get_assistant_message_html(message["content"], streaming=True, citation=citation), 
                unsafe_allow_html=True
            )
            
            # --- REFERENCES SECTION ---
            references = message.get("references")
            if references:
                st.markdown(
                    get_references_html(references),
                    unsafe_allow_html=True
                )
            
            # --- AUDIO CONTROLS ---
            if message.get("audio"):
                # The caption is the accessible alternative to the audio itself
                display_assistant_audio(
                    message["audio"],
                    autoplay=get_a11y_prefs().autoplay_audio,
                    transcript=describe_audio(
                        message["content"],
                        mode=st.session_state.get(f"tts_mode_{i}", "summary"),
                    ),
                )
            else:
                # State keys
                generating_key = f"generating_audio_{i}"
                preview_key = f"preview_summary_{i}"
                summary_key = f"summary_text_{i}"
                mode_key = f"tts_mode_{i}" 
                
                is_generating = st.session_state.get(generating_key, False)
                is_previewing = st.session_state.get(preview_key, False)
                
                # --- STATE 3: GENERATING ---
                if is_generating:
                    if backend:
                        mode = st.session_state.get(mode_key, "summary")
                        
                        if mode == "summary":
                            final_text = st.session_state.get(summary_key, message["content"])
                            use_summary_arg = False 
                        else:
                            final_text = message["content"]
                            use_summary_arg = False 

                        audio_bytes = generate_audio_with_progress(
                            backend, 
                            final_text,
                            i,
                            use_summary=use_summary_arg
                        )
                        
                        # Cleanup
                        st.session_state[generating_key] = False
                        st.session_state[preview_key] = False
                        if summary_key in st.session_state: del st.session_state[summary_key]
                        
                        if audio_bytes:
                            SessionState.update_message_audio(i, audio_bytes)
                            st.rerun()
                    else:
                        st.session_state[generating_key] = False
                        st.error("❌ Backend not initialized")
                
                # --- STATE 2: PREVIEWING (Summary Mode Only) ---
                elif is_previewing:
                    st.markdown("---")
                    st.markdown("**📝 Audio Script Preview** *(edited for clarity)*")
                    
                    # Generate Script if not cached
                    if summary_key not in st.session_state:
                        with st.spinner("✍️ AI is rewriting text for audio..."):
                            # --- FIX IS HERE ---
                            # Removed "and backend.summarizer" check.
                            # The backend now handles summarization internally via API.
                            if backend:
                                summary = backend.summarize_for_tts(message["content"])
                            else:
                                summary = message["content"][:600] # Fallback
                            # -------------------
                        st.session_state[summary_key] = summary
                    
                    # Edit Interface
                    edited_summary = st.text_area(
                        "Script:",
                        value=st.session_state[summary_key],
                        height=150,
                        key=f"edit_summary_{i}",
                        label_visibility="collapsed"
                    )
                    st.session_state[summary_key] = edited_summary
                    
                    # Controls
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.button(button_label("Generate Audio", "✅"), key=f"confirm_tts_{i}", type="primary", use_container_width=True):
                            st.session_state[mode_key] = "summary"
                            st.session_state[generating_key] = True
                            st.rerun()
                    with col2:
                        if st.button(button_label("Rewrite", "🔄"), key=f"regen_summary_{i}", use_container_width=True):
                            if summary_key in st.session_state: del st.session_state[summary_key]
                            st.rerun()
                    with col3:
                        if st.button(button_label("Cancel", "❌"), key=f"cancel_tts_{i}", use_container_width=True):
                            st.session_state[preview_key] = False
                            st.rerun()
                    st.markdown("---")
                
                # --- STATE 1: INITIAL BUTTONS ---
                else:
                    if len(message["content"]) < 600:
                         if st.button(button_label("Listen", "🔊"), key=f"tts_short_{i}", type="secondary"):
                            st.session_state[mode_key] = "full"
                            st.session_state[generating_key] = True
                            st.rerun()
                    else:
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button(button_label("Audio Script", "✨"), key=f"tts_summary_{i}", help="AI rewrites the response so it is easier to listen to"):
                                st.session_state[preview_key] = True
                                st.rerun()
                        with col2:
                            if st.button(button_label("Read Verbatim", "📖"), key=f"tts_full_{i}", help="Reads the exact text above aloud"):
                                st.session_state[mode_key] = "full"
                                st.session_state[generating_key] = True
                                st.rerun()

def render_input_area(config):
    """Render the input area with form."""
    # START: Wrap the form in the sticky container
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    with st.form(key="input_form", clear_on_submit=True):
        col1, col2 = st.columns([9, 1])
        
        with col1:
            query = st.text_input(
                "query",
                value="",
                placeholder=config.ui.input_placeholder,
                label_visibility="collapsed",
                key="user_input"
            )
        
        with col2:
            submit_button = st.form_submit_button("➤", type="primary", use_container_width=True)
            
    # END: Close the container div
    st.markdown('</div>', unsafe_allow_html=True)
    
    return query, submit_button


def process_user_query(query: str, backend: MedicalAIBackend, config):
    """
    Process a user query (Text Only).
    """
    # Update session state
    SessionState.set_current_query(query)
    SessionState.set_processing(True)
    SessionState.add_message("user", query)
    
    backend.flush_memory()
    
    citation_string = ""
    
    # Retrieve and generate response
    with st.spinner(config.ui.loading_message):
        best_chunk, citation_string, response_generator, references = backend.process_query(
            query, 
            top_k=config.generation.top_k_retrieval
        )
    
    # Stream the text response
    response_placeholder = st.empty()
    full_response = ""
    
    for token in response_generator:
        full_response += token
        response_placeholder.markdown(
            get_assistant_message_html(full_response, streaming=True, citation=citation_string),
            unsafe_allow_html=True
        )
    
    # Final text render
    # Don't re-render at all - the streaming version already has the correct content
    # Just let it stay as is (without the cursor, which will disappear naturally)
    # Re-rendering can cause HTML rendering issues
    # The streaming version already shows the content correctly
    
    # Save the message (user can click "Listen" manually)
    SessionState.add_message("assistant", full_response, citation=citation_string, references=references)
    
    # Log timing metrics after LLM response is complete
    # Note: TTS stages (summarize_tts_time, tts_audio_time) will be logged separately when user clicks audio button
    backend._log_timing_metrics(query)
    
    backend.flush_memory()
    SessionState.clear_current_query()
    SessionState.set_processing(False)
    
    st.rerun()


def main():
    """Main application entry point."""
    # Load configuration
    config = get_default_config()
    
    # Configure page
    configure_page(config)
    
    # Initialize session state
    SessionState.initialize()

    # Accessibility controls live in the sidebar; the resulting preferences feed the CSS
    a11y_prefs = render_accessibility_panel()

    # Inject base CSS plus the accessibility overrides
    inject_custom_css(a11y_prefs)
    
    # Check if models are loaded
    if not SessionState.is_models_loaded():
        # Show loading screen
        render_loading_screen(config)
        
        # Initialize backend
        backend = initialize_backend(config)
        SessionState.set_backend(backend)
        SessionState.set_models_loaded(True)
        
        # Rerun to show main interface
        st.rerun()
    
    # Get backend from session state
    backend = SessionState.get_backend()
    
    # Render header
    st.markdown(get_header(config.ui.app_name), unsafe_allow_html=True)
    
    # Render main content
    if not SessionState.has_conversation():
        render_welcome_screen(config)
    else:
        render_conversation()
    
    # Render input area with form
    query, submit_button = render_input_area(config)
    
    # Process query if submit button clicked
    if submit_button and query.strip() and not SessionState.is_processing():
        process_user_query(query, backend, config)
    
    # Render bottom navigation
    st.markdown(get_bottom_nav(), unsafe_allow_html=True)
    
    # Add bottom spacing
    st.markdown(get_bottom_spacing(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()