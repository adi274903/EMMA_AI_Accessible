"""
Backend module for medical AI consultation system.
Updated to use GenAI SDK for TTS and Summarization.
Now fully cloud-native for generation (Gemini 2.5 Flash Lite).
"""
import os
import gc
import csv
import re
import io
import wave
import base64
import json
import time
from typing import List, Tuple, Generator, Optional, Dict, Any

import torch
import chromadb
import psycopg2
import pgvector
import pgvector.psycopg2
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer, CrossEncoder

# --- CONSTANTS ---
GEMINI_CHAT_MODEL = "gemini-2.5-flash-lite"
# TTS model - uses the same GenAI client as chat
DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_TTS_VOICE = "Aoede"  # Options: Aoede, Puck, Charon, Kore, Fenrir, Leda

EMBED_MODEL_NAME = "abhinand/MedEmbed-large-v0.1"
RERANKER_MODEL_NAME = "ncbi/MedCPT-Cross-Encoder"
DEFAULT_SIMILARITY_THRESHOLD = 0.8

# Summarizer settings (Now using Gemini)
SUMMARIZE_THRESHOLD = 1500

ChunkData = Dict[str, Any]


class MedicalAIBackend:
    def __init__(self, vectorstore_path: str = "/content/medical_vectorstore", 
                 tts_model_name: str = DEFAULT_TTS_MODEL, 
                 tts_voice_name: str = DEFAULT_TTS_VOICE):
        self.vectorstore_path = vectorstore_path
        self.tts_model_name = tts_model_name
        self.tts_voice_name = tts_voice_name
        # Where to log retrievals
        self.retrieval_log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "retrieval_logs.csv",
        )
        # Where to log timing metrics
        self.timing_log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "timing_metrics.csv",
        )
        # Store timing data for current query
        self.current_timing = {}
        
        # Single GenAI client for Chat, TTS, and Summarization
        self.client: Optional[genai.Client] = None
        
        self.embed_model: Optional[SentenceTransformer] = None
        self.reranker: Optional[CrossEncoder] = None
        # Postgres (pgvector) connection string comes from the environment, e.g.
        #   export PG_CONN_STR="host=127.0.0.1 port=5432 dbname=ragdb user=postgres password=..."
        # No default is baked in: credentials must never live in the source tree.
        self.pg_conn_str = os.environ.get("PG_CONN_STR")
        self.pg_conn: Optional[psycopg2.extensions.connection] = None
        self.collection: Optional[chromadb.Collection] = None
        self.chat_session = None 
        self.last_response: Optional[str] = None
        
    def load_models(self) -> None:
        """Load all required models."""
        print("🔄 Backend: Loading models...")
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("❌ FATAL ERROR: GOOGLE_API_KEY not found.")
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        try:
            # Single GenAI Client for ALL generative tasks
            self.client = genai.Client(api_key=api_key)
            print(f"✅ GenAI Client initialized")
            
        except Exception as e:
            print(f"❌ Client Init Failed: {e}")
            raise e

        # Embedding & Reranker (Local Models)
        print("⏳ Loading Embedding Model...")
        self.embed_model = SentenceTransformer(
            EMBED_MODEL_NAME, 
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        self.reranker = CrossEncoder(RERANKER_MODEL_NAME, device="cpu")
        
        # Vector DB
        os.makedirs(self.vectorstore_path, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=self.vectorstore_path)
        self.collection = chroma_client.get_or_create_collection(name="harwood_nuss_medical_knowledge")
        # Postgres connection for enriched metadata (page lookup)
        self._init_pg_connection()

        # Chat Session
        system_instruction = (
            "You are an emergency medicine clinician. "
            "Provide detailed clinical responses based on reference material. "
            "Include thorough explanations , relevant context, relevant metrics and clinical reasoning."
        )
        
        # Create chat session
        self.chat_session = self.client.chats.create(
            model=GEMINI_CHAT_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3 # Keep it factual
            )
        )
        
        print("✅ All models loaded successfully.")

    def contextualize_query(self, new_query: str, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> str:
        if self.last_response is None: 
            return new_query
        embeddings = self.embed_model.encode([new_query, self.last_response], convert_to_tensor=True)
        similarity = torch.dot(embeddings[0], embeddings[1]).item()
        if similarity >= similarity_threshold:
            return f"The previous consultation advice was: '{self.last_response}'. Address this new related question: {new_query}"
        return new_query

    def _init_pg_connection(self) -> None:
        """Initialise (or reinitialise) the PostgreSQL connection for vector search."""
        if not self.pg_conn_str:
            raise ValueError("PG_CONN_STR environment variable is required for Postgres retrieval.")
        if self.pg_conn and not self.pg_conn.closed:
            return
        self.pg_conn = psycopg2.connect(self.pg_conn_str)
        pgvector.psycopg2.register_vector(self.pg_conn)

    def _get_pg_connection(self) -> psycopg2.extensions.connection:
        """Return a live PostgreSQL connection, recreating it if necessary."""
        if self.pg_conn is None or self.pg_conn.closed != 0:
            self._init_pg_connection()
        return self.pg_conn

    def retrieve_chunks(self, query: str, top_k: int = 20) -> List[ChunkData]:
        """Retrieve top_k relevant chunks from Chroma and enrich metadata with precise pages."""
        if not self.embed_model or not self.collection:
            raise RuntimeError("Backend models or vector store not initialized.")

        start_time = time.time()
        query_vector = self.embed_model.encode(query, convert_to_numpy=True).tolist()
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=['documents', 'metadatas']
        )
        raw_chunks = [
            {'document': d, 'metadata': (m or {})}
            for d, m in zip(results['documents'][0], results['metadatas'][0])
        ]
        # Enrich with precise page numbers from PostgreSQL metadata
        enriched = [self._attach_precise_page(chunk) for chunk in raw_chunks]
        elapsed = time.time() - start_time
        self.current_timing['retrieve_time'] = elapsed
        return enriched

    def _attach_precise_page(self, chunk: ChunkData) -> ChunkData:
        """Lookup precise page info from PostgreSQL metadata and attach if available."""
        # Ensure metadata dict exists and is mutable
        if 'metadata' not in chunk or chunk['metadata'] is None:
            chunk['metadata'] = {}
        meta = chunk['metadata']
        
        if meta.get('page'):
            return chunk  # already has page info

        source = meta.get('source')
        chunk_index = meta.get('chunk_index')
        if source is None or chunk_index is None:
            return chunk

        conn = self._get_pg_connection()
        sql = """
            SELECT metadata->>'page'
            FROM medical_embeddings
            WHERE metadata->>'source' = %s
              AND metadata->>'chunk_index' = %s
            LIMIT 1;
        """
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (source, str(chunk_index)))
                row = cur.fetchone()
            if row and row[0]:
                meta['page'] = row[0]
        except Exception as e:
            print(f"⚠️ Failed to fetch precise page info: {e}")
        return chunk
    
    def rerank_chunks(self, query: str, chunks: List[ChunkData]) -> List[Tuple[ChunkData, float]]:
        document_texts = [chunk['document'] for chunk in chunks]
        scores = self.reranker.predict([(query, text) for text in document_texts])
        return sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    
    def generate_response_stream(self, query: str, context: str) -> Generator[str, None, None]:
        start_time = time.time()
        full_query = f"**Reference:**\n{context}\n\n**Question:**\n{query}"
        response_stream = self.chat_session.send_message_stream(full_query)
        first_chunk_time = None
        for chunk in response_stream:
            if first_chunk_time is None:
                first_chunk_time = time.time()
                self.current_timing['llm_first_token_time'] = first_chunk_time - start_time
            yield chunk.text
        total_time = time.time() - start_time
        self.current_timing['llm_response_time'] = total_time
    
    def process_query(self, query: str, top_k: int = 20) -> Tuple[str, str, Generator[str, None, None], List[Dict[str, str]]]:
        """
        Main retrieval + generation pipeline.

        Also logs each retrieval to a CSV file:
        - First column: original question text (query)
        - Following columns: the raw documents used as LLM context
        """
        contextual_query = self.contextualize_query(query)
        chunks = self.retrieve_chunks(contextual_query, top_k=top_k)
        
        if not chunks:
             return "No relevant info found.", "", iter(["No relevant medical context found."]), []

        # Take top N chunks for context
        top_n = 20
        best_chunks_data = [c for c, s in self.rerank_chunks(contextual_query, chunks)[:top_n]]
        best_context = "\n---\n".join([d['document'] for d in best_chunks_data])
        
        # Build detailed references list (textbook + page)
        references = []
        for chunk_data in best_chunks_data:
            meta = chunk_data.get('metadata', {}) or {}
            source = meta.get('source', '') or ''
            page = meta.get('page')
            
            # Parse textbook name from source
            textbook_name = self._format_textbook_name(source)
            
            # Build reference entry
            if page:
                references.append({
                    'textbook': textbook_name,
                    'page': str(page)
                })
            else:
                # Fallback to page range from filename
                page_match = re.search(r"\(Pg_([^)]+)\)", source)
                if page_match:
                    references.append({
                        'textbook': textbook_name,
                        'page': page_match.group(1)
                    })
                else:
                    references.append({
                        'textbook': textbook_name,
                        'page': 'N/A'
                    })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_references = []
        for ref in references:
            ref_key = (ref['textbook'], ref['page'])
            if ref_key not in seen:
                seen.add(ref_key)
                unique_references.append(ref)
        
        # Build citation string (for backward compatibility)
        unique_sources = set(d['metadata'].get('source_file', d['metadata'].get('title', 'Medical KB')) for d in best_chunks_data)
        citation = "**Source(s):** " + " | ".join(unique_sources)

        # --- CSV LOGGING: question + each context chunk (+ textbook & page) ---
        try:
            os.makedirs(os.path.dirname(self.retrieval_log_path), exist_ok=True)
            file_exists = os.path.exists(self.retrieval_log_path)
            with open(self.retrieval_log_path, mode="a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                # Write header if file newly created
                if not file_exists:
                    header = ["question"]
                    for i in range(top_n):
                        idx = i + 1
                        header.extend(
                            [
                                f"context_{idx}",
                                f"context_{idx}_textbook",
                                f"context_{idx}_page",
                            ]
                        )
                    writer.writerow(header)
                # Build row: question + (context, textbook, page) * top_n
                row = [query]
                for i in range(top_n):
                    if i < len(best_chunks_data):
                        meta = best_chunks_data[i].get("metadata", {}) or {}
                        doc_text = best_chunks_data[i].get("document", "")
                        source = meta.get("source", "") or ""

                        # Parse textbook name & fallback page_info from source filename
                        textbook_name = source
                        fallback_page_info = ""
                        source_page_match = re.search(r"\(Pg_([^)]+)\)", source)
                        if source_page_match:
                            fallback_page_info = source_page_match.group(1)
                            split_token = "_----_("
                            if split_token in source:
                                textbook_name = source.split(split_token)[0]

                        # Prefer precise page number if metadata contains it
                        page_number = meta.get("page")
                        if page_number is not None:
                            page_info = str(page_number)
                        else:
                            page_info = fallback_page_info

                        row.extend([doc_text, textbook_name, page_info])
                    else:
                        # No context for this slot
                        row.extend(["", "", ""])

                writer.writerow(row)
        except Exception as e:
            # Fail silently for logging so it never breaks main flow
            print(f"⚠️ Failed to log retrieval to CSV: {e}")
        
        self.last_response = query 
        self.current_timing['query'] = query  # Store query for later logging
        
        return best_context, citation, self.generate_response_stream(contextual_query, best_context), unique_references

    def _format_textbook_name(self, source: str) -> str:
        """Convert source filename into a human-readable textbook title."""
        if not source:
            return "Unknown Reference"
        
        name = source
        if '_----_(' in name:
            name = name.split('_----_(')[0]
        if '.pdf' in name:
            name = name.replace('.pdf', '')
        
        name = name.replace('_', ' ')
        name = name.replace('...', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        
        if not name:
            return "Unknown Reference"
        return name
    
    def summarize_for_tts(self, text: str) -> str:
        """
        Mode 1: Audio Script Writer.
        Uses Gemini Flash Lite to rewrite text for clear speech while preserving metrics.
        """
        # 1. Safety Check
        if len(text) < 1000:
            return text
        
        start_time = time.time()
        print(f"📝 Generating Audio Script ({len(text)} chars) with Gemini...")
        
        try:
            # Scripting Prompt
            prompt = (
                "You are a Medical Audio Script Writer. Your task is to rewrite the input text for clear speech synthesis.\n\n"
                "STRICT RULES:\n"
                "1. PRESERVE ALL NUMBERS: Keep every specific metric, dosage, and score point.\n"
                "2. OPTIMIZE FOR FLOW: Remove markdown symbols (**, #) that are hard to read, but keep the data.\n"
                "3. NO FLUFF: Remove introductory phrases like 'Here is the response'.\n"
                "4. CONCISE: Shorten lengthy explanations while retaining meaning.\n"
                f"INPUT TEXT:\n{text}"
            )

            # Use the same client model for lightweight task
            response = self.client.models.generate_content(
                model=GEMINI_CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2, # Strict adherence
                    max_output_tokens=2000
                )
            )
            
            script = response.text.strip()
            
            # Sanity check
            if len(script) < (len(text) * 0.2):
                print("⚠️ Script too short, reverting.")
                return text[:4000]

            print(f"✅ Script Generated: {len(text)} chars -> {len(script)} chars")
            return script
            
        except Exception as e:
            print(f"⚠️ Script generation failed: {e}")
            return text[:4000]

    def generate_speech(self, text: str, use_summary: bool = True) -> Optional[bytes]:
        """
        Generate audio with a user-selected mode.
        """
        if not text:
            return None
        if not self.client:
            print("❌ GenAI Client not initialized.")
            return None
        
        tts_start_time = time.time()
        # --- SELECTION LOGIC ---
        if use_summary:
            print("🎙️ Mode: SUMMARY (Script Writer)")
            text_for_tts = self.summarize_for_tts(text)
        else:
            print("🎙️ Mode: FULL TEXT (Verbatim)")
            text_for_tts = text[:9000] if len(text) > 9000 else text
            if len(text) > 9000:
                print("⚠️ Text exceeded 9000 chars, truncated end for TTS stability.")

        print(f"📝 TTS input length: {len(text_for_tts)} characters")

        try:
            response = self.client.models.generate_content(
                model=self.tts_model_name,
                contents=text_for_tts,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.tts_voice_name
                            )
                        )
                    )
                )
            )

            if response.candidates and response.candidates[0].content.parts:
                audio_part = response.candidates[0].content.parts[0]
                if hasattr(audio_part, 'inline_data'):
                    # Decode Base64 if string, else use bytes directly
                    raw_data = audio_part.inline_data.data
                    pcm_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data
                    elapsed = time.time() - tts_start_time
                    self.current_timing['tts_audio_time'] = elapsed
                    return self._pcm_to_wav(pcm_bytes)

            elapsed = time.time() - tts_start_time
            self.current_timing['tts_audio_time'] = elapsed
            print("❌ No audio data in response")
            return None

        except Exception as e:
            elapsed = time.time() - tts_start_time
            self.current_timing['tts_audio_time'] = elapsed
            print(f"❌ TTS Generation Failed: {e}")
            return None

    def _log_timing_metrics(self, query: str) -> None:
        """Log timing metrics to CSV file."""
        try:
            file_exists = os.path.exists(self.timing_log_path)
            with open(self.timing_log_path, mode="a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    header = [
                        "query",
                        "retrieve_time",
                        "llm_response_time",
                        "llm_first_token_time",
                        "summarize_tts_time",
                        "tts_audio_time",
                        "total_time"
                    ]
                    writer.writerow(header)
                
                # Calculate total time
                total = (
                    self.current_timing.get('retrieve_time', 0) +
                    self.current_timing.get('llm_response_time', 0) +
                    self.current_timing.get('summarize_tts_time', 0) +
                    self.current_timing.get('tts_audio_time', 0)
                )
                
                row = [
                    query[:200],  # Truncate long queries
                    round(self.current_timing.get('retrieve_time', 0), 3),
                    round(self.current_timing.get('llm_response_time', 0), 3),
                    round(self.current_timing.get('llm_first_token_time', 0), 3),
                    round(self.current_timing.get('summarize_tts_time', 0), 3),
                    round(self.current_timing.get('tts_audio_time', 0), 3),
                    round(total, 3)
                ]
                writer.writerow(row)
            
            # Reset timing for next query
            self.current_timing = {}
        except Exception as e:
            print(f"⚠️ Failed to log timing metrics: {e}")

    def _pcm_to_wav(self, pcm_data: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(rate)
            wav_file.writeframes(pcm_data)

        wav_buffer.seek(0)
        return wav_buffer.read()

    @staticmethod
    def flush_memory():
        gc.collect()
        if torch.cuda.is_available(): 
            torch.cuda.empty_cache()