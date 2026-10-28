"""
Configuration settings for the medical AI consultation application.
Updated to use GenAI SDK for TTS (same API key as chat).
"""

import os

from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelConfig:
    """Configuration for AI models."""
    
    # CHAT Model (Text Generation)
    llm_repo_id: str = "gemini-2.5-flash-lite"
    
    # TTS Configuration - Now uses GenAI SDK (same API key as chat!)
    # Available voices: Aoede, Puck, Charon, Kore, Fenrir, Leda
    tts_model_name: str = "gemini-2.5-flash-preview-tts"
    tts_voice_name: str = "Aoede"
    
    # Embedding Model
    embed_model_name: str = "abhinand/MedEmbed-large-v0.1"
    embed_device: str = "cuda"
    
    # Reranker Model
    reranker_model_name: str = "ncbi/MedCPT-Cross-Encoder"
    reranker_device: str = "cpu"
    
    # Vector store directory. Override with the MEDICAL_VECTORSTORE_PATH environment
    # variable; the default is a repo-relative path so nothing machine-specific is baked in.
    vectorstore_path: str = os.environ.get("MEDICAL_VECTORSTORE_PATH", "./medical_vectorstore")
    collection_name: str = "harwood_nuss_medical_knowledge"


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_k_retrieval: int = 20
    stop_sequences: list = None
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["</s>", "<end_of_turn>"]


@dataclass
class UIConfig:
    """Configuration for the user interface."""
    page_title: str = "EMMA AI - Accessible"
    page_icon: str = "🎧"
    layout: str = "centered"
    initial_sidebar_state: str = "collapsed"
    app_name: str = "EMMA AI"
    doctor_name: str = "Clinician"
    input_placeholder: str = "Type your question here..."
    loading_message: str = "🔍 Searching medical knowledge base..."
    tts_loading_message: str = "🎙️ Generating audio response..."


@dataclass
class AppConfig:
    """Master configuration combining all settings."""
    model: ModelConfig = None
    generation: GenerationConfig = None
    ui: UIConfig = None
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        if self.generation is None:
            self.generation = GenerationConfig()
        if self.ui is None:
            self.ui = UIConfig()

def get_default_config() -> AppConfig:
    return AppConfig()