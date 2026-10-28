#!/usr/bin/env python3
"""
Automated pipeline timing test script.
Tests each stage of the medical AI consultation pipeline and logs timing metrics to CSV.
"""

import os
import sys
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️ .env file not found at {env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed, skipping .env file loading")
    load_dotenv = None

from backend import MedicalAIBackend
from config import get_default_config

# Test questions - Add your questions here
TEST_QUESTIONS = [
    # Pulmonary Embolism Questions
    "What are the different scoring tools available that a clinician in the Emergency Department can utilize to help determine what testing needs ordered when considering a pulmonary embolism as a differential diagnosis?",
    "When concerned that a patient may have a pulmonary embolism in the emergency department, in addition to a D-Dimer or CT PE, what other diagnostic tests should a clinician immediately order?",
    "What signs, symptoms and testing results can be utilized in the Emergency Department to help risk stratify a patient with a newly diagnosed Pulmonary Embolism?",
    "What risk factors increase the probability that a patient may develop a pulmonary embolism?",
    "Once a patient is diagnosed with a Pulmonary Embolism, how do I differentiate which patients must be admitted to the hospital for IV thrombolytics and which patients can be discharged home on oral anticoagulation, like Eliquis?",
    "Why could I consider VV-ECMO as a potential therapy for an unstable patient with a newly diagnosed saddle pulmonary embolism?",
    
    # Myxedema Coma Questions
    "What emergent signs and symptoms may a patient present to the Emergency Department with that would cause you to consider Myxedema Coma as your top differential?",
    "If I am concerned that a patient has decompensated hypothyroidism on initial exam in the Emergency Department, in addition to stabilizing the patient, what other tests should I order or consider?",
    "What medical treatment should I provide emergently to a patient that I am concerned has decompensated hypothyroidism?",
    "What are some of the triggers in which a patient with well controlled hypothyroidism, can all of the sudden develop decompensated hypothyroidism?",
    "Why did my patient we diagnosed with a myxedema coma require an emergent intubation due to developing acute respiratory failure?",
    "What complications can occur if a patient with Myxedema Coma receives thyroid hormone therapy without appropriate steroid coverage, and why is this dangerous?",
]


def test_pipeline(backend: MedicalAIBackend, query: str, config):
    """
    Test the complete pipeline for a single query.
    
    Args:
        backend: Initialized MedicalAIBackend instance
        query: Test question
        config: Application configuration
    """
    print(f"\n{'='*80}")
    print(f"Testing Query: {query[:100]}...")
    print(f"{'='*80}")
    
    try:
        # Stage 1: Retrieve chunks (timing logged in retrieve_chunks)
        print("\n[Stage 1] Retrieving chunks...")
        best_chunk, citation_string, response_generator, references = backend.process_query(
            query,
            top_k=config.generation.top_k_retrieval
        )
        
        # Stage 2: Generate LLM response (timing logged in generate_response_stream)
        print("\n[Stage 2] Generating LLM response...")
        full_response = ""
        for token in response_generator:
            full_response += token
        print(f"Response length: {len(full_response)} characters")
        
        # Stage 3: Generate TTS script (timing logged in summarize_for_tts)
        print("\n[Stage 3] Generating TTS script...")
        script = backend.summarize_for_tts(full_response)
        print(f"Script length: {len(script)} characters")
        
        # Stage 4: Generate audio (timing logged in generate_speech)
        print("\n[Stage 4] Generating audio...")
        audio_bytes = backend.generate_speech(full_response, use_summary=True)
        if audio_bytes:
            print(f"Audio generated: {len(audio_bytes)} bytes")
        else:
            print("⚠️ Audio generation failed")
        
        # Log timing metrics after all stages complete
        backend._log_timing_metrics(query)
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"Timing metrics logged to: {backend.timing_log_path}")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test runner."""
    if not TEST_QUESTIONS:
        print("⚠️ No test questions provided. Please add questions to TEST_QUESTIONS list.")
        print("\nExample:")
        print('TEST_QUESTIONS = [')
        print('    "What are the different scoring tools available...",')
        print('    "What signs, symptoms and testing results...",')
        print(']')
        sys.exit(1)
    
    # Check for required environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_api_key:
        print("❌ FATAL ERROR: API key not found.")
        print("   Please set one of the following environment variables:")
        print("   - GOOGLE_API_KEY (preferred)")
        print("   - GEMINI_API_KEY (alternative)")
        print("\n   You can:")
        print("   1. Set it in your shell: export GOOGLE_API_KEY='your_key_here'")
        print("   2. Create a .env file in the EMMA_AI_Accessible directory with: GOOGLE_API_KEY=your_key_here")
        sys.exit(1)
    
    # If GEMINI_API_KEY is set but GOOGLE_API_KEY is not, set it for compatibility
    if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
        print("ℹ️  Using GEMINI_API_KEY as GOOGLE_API_KEY for compatibility")
    
    print("🚀 Starting Pipeline Timing Tests")
    print(f"Number of test questions: {len(TEST_QUESTIONS)}")
    
    # Load configuration
    config = get_default_config()
    
    # Initialize backend
    print("\n⏳ Initializing backend models...")
    backend = MedicalAIBackend(
        vectorstore_path=config.model.vectorstore_path,
        tts_model_name=config.model.tts_model_name,
        tts_voice_name=config.model.tts_voice_name
    )
    backend.load_models()
    print("✅ Backend initialized")
    
    # Run tests
    for i, query in enumerate(TEST_QUESTIONS, 1):
        print(f"\n\n{'#'*80}")
        print(f"# Test {i}/{len(TEST_QUESTIONS)}")
        print(f"{'#'*80}")
        test_pipeline(backend, query, config)
        
        # Flush memory between tests
        backend.flush_memory()
    
    print(f"\n\n{'='*80}")
    print("✅ All tests completed!")
    print(f"📊 Timing metrics saved to: {backend.timing_log_path}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

