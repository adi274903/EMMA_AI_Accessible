"""
Utility script to run the EMMA AI Streamlit app on a local VM (no Colab).

What it does:
- Loads a local .env file (optional) so API keys and connection strings can live there
- Checks that the required environment variables are set (GOOGLE_API_KEY above all)
- Checks whether the vector-store directory exists and tells you what to do if it does not
- Starts the Streamlit app (app_refactored.py) as a subprocess
"""

import os
import sys
import subprocess
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR


def load_env():
    """
    Load .env when python-dotenv is installed and the file exists.

    The dependency is optional so the script still works in a bare environment.
    """
    env_path = PROJECT_DIR / ".env"
    if load_dotenv is not None and env_path.exists():
        load_dotenv(env_path)


def check_env():
    """
    Check the required environment variables.

    The backend reads GOOGLE_API_KEY (Gemini chat, TTS and summarisation); GEMINI_API_KEY
    is accepted as an alias and copied across so either name works.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not google_api_key:
        print("Missing environment variable: GOOGLE_API_KEY (or GEMINI_API_KEY)")
        print("Set it in .env or in the current shell, for example:")
        print("   export GOOGLE_API_KEY='your_api_key_here'")
        sys.exit(1)
    os.environ.setdefault("GOOGLE_API_KEY", google_api_key)


def check_vectorstore():
    """
    Check whether the vector-store directory exists.

    MEDICAL_VECTORSTORE_PATH wins; otherwise the default from config.py is used.
    """
    from config import get_default_config

    cfg = get_default_config()
    default_path = Path(cfg.model.vectorstore_path)
    env_override = os.getenv("MEDICAL_VECTORSTORE_PATH")
    vectorstore_path = Path(env_override) if env_override else default_path

    if not vectorstore_path.exists():
        print("Vector-store directory not found:", vectorstore_path)
        print("   Copy or unpack an already-built vector store into that directory,")
        print("   or set MEDICAL_VECTORSTORE_PATH to point at the real path.")
    else:
        print("Vector-store directory found:", vectorstore_path)


def run_streamlit():
    """
    Start the Streamlit app for a local VM.

    Port defaults to 8501 and can be overridden with the STREAMLIT_PORT environment variable.
    """
    port = os.getenv("STREAMLIT_PORT", "8501")

    app_path = PROJECT_DIR / "app_refactored.py"
    if not app_path.exists():
        print(f"Cannot find the application entry point: {app_path}")
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]

    print("Starting the Streamlit app...")
    print("   command:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Streamlit failed to start, exit code: {e.returncode}")
        sys.exit(e.returncode)


def main():
    load_env()
    check_env()
    check_vectorstore()
    run_streamlit()


if __name__ == "__main__":
    main()
