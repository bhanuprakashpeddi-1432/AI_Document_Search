from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from .config import settings


# Bearer token security scheme
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the Bearer token from the request
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        str: The verified token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != settings.BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


def validate_api_keys() -> bool:
    """
    Validate that all required API keys are present
    
    Returns:
        bool: True if all keys are valid, False otherwise
    """
    required_keys = {
        "OpenAI API Key": settings.OPENAI_API_KEY,
        "Pinecone API Key": settings.PINECONE_API_KEY,
        "Pinecone Environment": settings.PINECONE_ENV,
        "PostgreSQL URL": settings.POSTGRES_URL
    }
    
    missing_keys = [name for name, key in required_keys.items() if not key]
    
    if missing_keys:
        print(f"Missing required configuration: {', '.join(missing_keys)}")
        return False
    
    return True


class SecurityHeaders:
    """Security headers for API responses"""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get standard security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
