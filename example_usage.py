"""
Example: Using the backend independently from Streamlit.
This demonstrates how the modular architecture allows the backend
to be used in other contexts (CLI, API, scripts, etc.)
"""

from backend import MedicalAIBackend
from config import get_default_config


def simple_cli_example():
    """Simple command-line interface example."""
    print("Medical AI Consultation - CLI Mode")
    print("=" * 50)
    
    # Load configuration
    config = get_default_config()
    
    # Initialize backend
    print("\nLoading models...")
    backend = MedicalAIBackend(vectorstore_path=config.model.vectorstore_path)
    backend.load_models()
    print("✓ Models loaded successfully!\n")
    
    # Example query
    query = "What are the indications for IV levothyroxine?"
    print(f"Query: {query}\n")
    
    # Process query
    print("Searching medical knowledge base...")
    best_chunk, response_generator = backend.process_query(query, top_k=20)
    
    print("\nClinical Response:")
    print("-" * 50)
    
    # Stream the response
    full_response = ""
    for token in response_generator:
        print(token, end="", flush=True)
        full_response += token
    
    print("\n" + "=" * 50)
    print(f"\nResponse length: {len(full_response)} characters")
    
    # Clean up
    backend.flush_gpu_memory()


def batch_processing_example():
    """Example of processing multiple queries in batch."""
    print("\nBatch Processing Example")
    print("=" * 50)
    
    # Load configuration
    config = get_default_config()
    
    # Initialize backend
    print("\nLoading models...")
    backend = MedicalAIBackend(vectorstore_path=config.model.vectorstore_path)
    backend.load_models()
    print("✓ Models loaded successfully!\n")
    
    # Multiple queries
    queries = [
        "What are the signs of sepsis?",
        "How do you treat anaphylaxis?",
        "What are the contraindications for tPA?"
    ]
    
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\nProcessing query {i}/{len(queries)}: {query}")
        
        # Process query
        best_chunk, response_generator = backend.process_query(query, top_k=20)
        
        # Collect full response
        full_response = ""
        for token in response_generator:
            full_response += token
        
        results.append({
            "query": query,
            "response": full_response,
            "context": best_chunk
        })
        
        print(f"✓ Completed ({len(full_response)} chars)")
        
        # Clean up between queries
        backend.flush_gpu_memory()
    
    print("\n" + "=" * 50)
    print(f"Processed {len(results)} queries successfully!")
    
    return results


def rag_pipeline_example():
    """Example showing individual RAG pipeline steps."""
    print("\nRAG Pipeline Step-by-Step Example")
    print("=" * 50)
    
    # Load configuration
    config = get_default_config()
    
    # Initialize backend
    print("\nLoading models...")
    backend = MedicalAIBackend(vectorstore_path=config.model.vectorstore_path)
    backend.load_models()
    print("✓ Models loaded!\n")
    
    query = "What are the symptoms of myocardial infarction?"
    print(f"Query: {query}\n")
    
    # Step 1: Retrieve
    print("Step 1: Retrieving relevant chunks...")
    chunks = backend.retrieve_chunks(query, top_k=20)
    print(f"✓ Retrieved {len(chunks)} chunks")
    
    # Step 2: Rerank
    print("\nStep 2: Reranking chunks by relevance...")
    reranked = backend.rerank_chunks(query, chunks)
    print(f"✓ Reranked {len(reranked)} chunks")
    
    # Show top 3 scores
    print("\nTop 3 most relevant chunks:")
    for i, (chunk, score) in enumerate(reranked[:3], 1):
        print(f"  {i}. Score: {score:.4f} | Preview: {chunk[:80]}...")
    
    # Step 3: Generate
    print("\nStep 3: Generating response...")
    best_chunk, _ = reranked[0]
    response_generator = backend.generate_response_stream(query, best_chunk)
    
    full_response = ""
    for token in response_generator:
        full_response += token
    
    print(f"✓ Generated response ({len(full_response)} chars)")
    print("\nResponse preview:")
    print("-" * 50)
    print(full_response[:200] + "...")
    print("-" * 50)
    
    # Clean up
    backend.flush_gpu_memory()


if __name__ == "__main__":
    # Run examples
    print("\n🏥 Medical AI Backend Examples\n")
    
    # Choose which example to run
    example_choice = input(
        "Choose example:\n"
        "1. Simple CLI\n"
        "2. Batch Processing\n"
        "3. RAG Pipeline Steps\n"
        "Enter choice (1-3): "
    ).strip()
    
    if example_choice == "1":
        simple_cli_example()
    elif example_choice == "2":
        batch_processing_example()
    elif example_choice == "3":
        rag_pipeline_example()
    else:
        print("Invalid choice. Running simple CLI example...")
        simple_cli_example()