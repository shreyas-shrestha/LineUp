# config.py - Centralized Configuration Management
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration with validation"""
    
    # Server Configuration
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
    MODAL_HAIRFAST_ENDPOINT = os.getenv("MODAL_HAIRFAST_ENDPOINT", "")
    HF_API_KEY = os.getenv("HF_API_KEY", "") or os.getenv("HUGGINGFACE_API_KEY", "")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
    
    # Database (SQLite by default - no setup needed!)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///lineup.db")
    
    # Redis (optional - falls back to in-memory)
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # Rate Limiting
    RATE_LIMIT_STORAGE = REDIS_URL if REDIS_URL else "memory://"
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://lineupai.onrender.com,http://localhost:*,*").split(",")
    
    # Cache Settings
    CACHE_DURATION = int(os.getenv("CACHE_DURATION", 3600))  # 1 hour
    
    # API Rate Limits (free tier)
    PLACES_API_DAILY_LIMIT = int(os.getenv("PLACES_API_DAILY_LIMIT", 100))
    GEMINI_API_DAILY_LIMIT = int(os.getenv("GEMINI_API_DAILY_LIMIT", 50))
    
    @classmethod
    def validate(cls) -> dict:
        """Validate configuration and return status"""
        warnings = []
        info = []
        
        # Check critical APIs
        if not cls.GEMINI_API_KEY:
            warnings.append("GEMINI_API_KEY not set - will use mock data")
        else:
            info.append("✓ Gemini API configured")
        
        if not cls.GOOGLE_PLACES_API_KEY:
            warnings.append("GOOGLE_PLACES_API_KEY not set - will use mock barber data")
        else:
            info.append("✓ Google Places API configured")
        
        if not cls.MODAL_HAIRFAST_ENDPOINT and not cls.HF_API_KEY:
            warnings.append("HairFastGAN not configured - virtual try-on disabled")
        else:
            info.append("✓ Virtual try-on configured")
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"⚠️  {warning}")
        
        for item in info:
            logger.info(f"✅ {item}")
        
        return {
            "warnings": warnings,
            "info": info,
            "database": cls.DATABASE_URL,
            "cache": "Redis" if cls.REDIS_URL else "Memory",
            "debug": cls.DEBUG
        }
    
    @classmethod
    def get_status(cls) -> dict:
        """Get configuration status for health endpoint"""
        return {
            "gemini_configured": bool(cls.GEMINI_API_KEY),
            "places_api_configured": bool(cls.GOOGLE_PLACES_API_KEY),
            "hairfast_configured": bool(cls.MODAL_HAIRFAST_ENDPOINT or cls.HF_API_KEY),
            "database": "sqlite" if "sqlite" in cls.DATABASE_URL else "postgresql",
            "cache_backend": "redis" if cls.REDIS_URL else "memory",
            "debug_mode": cls.DEBUG
        }

