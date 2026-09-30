import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

    # --- Database -----------------------------------------------------
    # Defaults to a local SQLite file so the app runs with zero setup.
    # To move to MySQL, set DATABASE_URL, e.g.:
    #   mysql+pymysql://user:password@host:3306/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'learning_companion.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Local Ollama AI ------------------------------------------------
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
    OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
    OLLAMA_TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.2"))
    OLLAMA_MAX_TRANSCRIPT_CHARS = int(os.environ.get("OLLAMA_MAX_TRANSCRIPT_CHARS", "45000"))

    # --- Misc -----------------------------------------------------------
    EXPORT_FOLDER = os.path.join(basedir, "exports")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"
