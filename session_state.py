"""
Session state management for the Streamlit application.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


class SessionState:
    """Manages Streamlit session state with type-safe access."""
    
    # State keys
    MESSAGES = "messages"
    MODELS_LOADED = "models_loaded"
    PROCESSING = "processing"
    CURRENT_QUERY = "current_query"
    BACKEND = "backend"
    LAST_ASSISTANT_AUDIO = "last_assistant_audio"
    
    @staticmethod
    def initialize() -> None:
        """Initialize all session state variables if they don't exist."""
        if SessionState.MESSAGES not in st.session_state:
            st.session_state[SessionState.MESSAGES] = []
        
        if SessionState.MODELS_LOADED not in st.session_state:
            st.session_state[SessionState.MODELS_LOADED] = False
        
        if SessionState.PROCESSING not in st.session_state:
            st.session_state[SessionState.PROCESSING] = False
        
        if SessionState.CURRENT_QUERY not in st.session_state:
            st.session_state[SessionState.CURRENT_QUERY] = ""
        
        if SessionState.BACKEND not in st.session_state:
            st.session_state[SessionState.BACKEND] = None
        
        if SessionState.LAST_ASSISTANT_AUDIO not in st.session_state:
            st.session_state[SessionState.LAST_ASSISTANT_AUDIO] = None
    
    @staticmethod
    def get_messages() -> List[Dict[str, str]]:
        """
        Get the conversation message history.
        
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        return st.session_state.get(SessionState.MESSAGES, [])
    
    @staticmethod
    def add_message(role: str, content: str, citation: Optional[str] = None, references: Optional[List[Dict[str, str]]] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            citation: Optional citation string (for assistant messages)
            references: Optional list of reference dicts with 'textbook' and 'page' keys
        """
        if SessionState.MESSAGES not in st.session_state:
            st.session_state[SessionState.MESSAGES] = []
        
        # Build the message dictionary
        message_data = {
            "role": role,
            "content": content
        }
        
        # Only add citation and references if provided and the message is from the assistant
        if role == "assistant":
            if citation:
                message_data["citation"] = citation
            if references:
                message_data["references"] = references

        st.session_state[SessionState.MESSAGES].append(message_data)
    
    @staticmethod
    def clear_messages() -> None:
        """Clear all conversation messages and reset last assistant audio."""
        st.session_state[SessionState.MESSAGES] = []
        st.session_state[SessionState.LAST_ASSISTANT_AUDIO] = None
    
    @staticmethod
    def is_models_loaded() -> bool:
        """
        Check if models are loaded.
        
        Returns:
            True if models are loaded, False otherwise
        """
        return st.session_state.get(SessionState.MODELS_LOADED, False)
    
    @staticmethod
    def set_models_loaded(loaded: bool) -> None:
        """
        Set the models loaded state.
        
        Args:
            loaded: Whether models are loaded
        """
        st.session_state[SessionState.MODELS_LOADED] = loaded
    
    @staticmethod
    def is_processing() -> bool:
        """
        Check if currently processing a query.
        
        Returns:
            True if processing, False otherwise
        """
        return st.session_state.get(SessionState.PROCESSING, False)
    
    @staticmethod
    def set_processing(processing: bool) -> None:
        """
        Set the processing state.
        
        Args:
            processing: Whether currently processing
        """
        st.session_state[SessionState.PROCESSING] = processing
    
    @staticmethod
    def get_current_query() -> str:
        """
        Get the current query being processed.
        
        Returns:
            Current query string
        """
        return st.session_state.get(SessionState.CURRENT_QUERY, "")
    
    @staticmethod
    def set_current_query(query: str) -> None:
        """
        Set the current query.
        
        Args:
            query: Query string
        """
        st.session_state[SessionState.CURRENT_QUERY] = query
    
    @staticmethod
    def clear_current_query() -> None:
        """Clear the current query."""
        st.session_state[SessionState.CURRENT_QUERY] = ""
    
    @staticmethod
    def get_backend() -> Optional[Any]:
        """
        Get the backend instance.
        
        Returns:
            Backend instance or None
        """
        return st.session_state.get(SessionState.BACKEND)
    
    @staticmethod
    def set_backend(backend: Any) -> None:
        """
        Set the backend instance.
        
        Args:
            backend: Backend instance
        """
        st.session_state[SessionState.BACKEND] = backend
    
    @staticmethod
    def has_conversation() -> bool:
        """
        Check if there are any messages in the conversation.
        
        Returns:
            True if messages exist, False otherwise
        """
        return len(SessionState.get_messages()) > 0
    
    @staticmethod
    def get_conversation_length() -> int:
        """
        Get the number of messages in the conversation.
        
        Returns:
            Number of messages
        """
        return len(SessionState.get_messages())
    
    @staticmethod
    def update_message_audio(index: int, audio_data: bytes) -> None:
        """
        Update a specific message in history with audio data.
        
        Args:
            index: The index of the message in the list
            audio_data: The binary audio data to save
        """
        if SessionState.MESSAGES in st.session_state:
            messages = st.session_state[SessionState.MESSAGES]
            if 0 <= index < len(messages):
                messages[index]["audio"] = audio_data

    @staticmethod
    def get_last_assistant_audio() -> Optional[bytes]:
        """
        Get the audio data (e.g., MP3/WAV bytes) for the last assistant response.
        
        Returns:
            Binary audio data or None.
        """
        return st.session_state.get(SessionState.LAST_ASSISTANT_AUDIO)
        
    @staticmethod
    def set_last_assistant_audio(audio_data: Optional[bytes]) -> None:
        """
        Set the audio data for the last assistant response.
        
        Args:
            audio_data: Binary audio data to store.
        """
        st.session_state[SessionState.LAST_ASSISTANT_AUDIO] = audio_data
