import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENV: str = os.getenv("PINECONE_ENV", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "hackrx-index")
    
    # Database
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "")
    
    # Security
    BEARER_TOKEN: str = os.getenv("BEARER_TOKEN", "hackrx-default-token")
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    
    # Vector Search
    TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "10"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are present"""
        required_settings = [
            self.OPENAI_API_KEY,
            self.PINECONE_API_KEY,
            self.PINECONE_ENV,
            self.POSTGRES_URL
        ]
        return all(setting for setting in required_settings)


# Global settings instance
settings = Settings()
