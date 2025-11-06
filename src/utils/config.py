"""Configuration management utility."""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager for application settings."""
    
    # YouTube API
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
    YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID', '')
    YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')
    
    # OAuth
    OAUTH_TOKEN_FILE = os.getenv('OAUTH_TOKEN_FILE', 'config/youtube_token.json')
    OAUTH_CREDENTIALS_FILE = os.getenv('OAUTH_CREDENTIALS_FILE', 'config/client_secrets.json')
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
    # Anthropic
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229')
    
    # Google AI (Gemini)
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', '')
    GOOGLE_AI_MODEL = os.getenv('GOOGLE_AI_MODEL', 'gemini-pro')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///youtube_seo.db')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Notifications
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
    EMAIL_SMTP_HOST = os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com')
    EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    EMAIL_FROM = os.getenv('EMAIL_FROM', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_TO = os.getenv('EMAIL_TO', '')
    
    # Performance Guardrails
    GUARDRAIL_CTR_DROP_THRESHOLD = float(os.getenv('GUARDRAIL_CTR_DROP_THRESHOLD', '15'))
    GUARDRAIL_IMPRESSIONS_VARIANCE = float(os.getenv('GUARDRAIL_IMPRESSIONS_VARIANCE', '10'))
    GUARDRAIL_CHECK_DAYS = int(os.getenv('GUARDRAIL_CHECK_DAYS', '3'))
    GUARDRAIL_BASELINE_DAYS = int(os.getenv('GUARDRAIL_BASELINE_DAYS', '7'))
    
    # Application Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '20'))
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')
    
    # Character Limits
    MAX_TITLE_LENGTH = int(os.getenv('MAX_TITLE_LENGTH', '100'))
    MAX_DESCRIPTION_LENGTH = int(os.getenv('MAX_DESCRIPTION_LENGTH', '5000'))
    MAX_TAGS_LENGTH = 380  # YouTube actual limit is ~400 chars for all tags combined, using 380 to be safe
    
    # Feature Flags
    ENABLE_AUTO_ROLLBACK = os.getenv('ENABLE_AUTO_ROLLBACK', 'true').lower() == 'true'
    ENABLE_SCHEDULED_REOPTIMIZATION = os.getenv('ENABLE_SCHEDULED_REOPTIMIZATION', 'true').lower() == 'true'
    ENABLE_ASR_FALLBACK = os.getenv('ENABLE_ASR_FALLBACK', 'false').lower() == 'true'
    ENABLE_YT_SCHEDULING = os.getenv('ENABLE_YT_SCHEDULING', 'true').lower() == 'true'
    ENABLE_YT_MONETIZATION_FLOW = os.getenv('ENABLE_YT_MONETIZATION_FLOW', 'true').lower() == 'true'
    MONETIZATION_NOTIFY_SLACK = os.getenv('MONETIZATION_NOTIFY_SLACK', 'true').lower() == 'true'
    MONETIZATION_NOTIFY_EMAIL = os.getenv('MONETIZATION_NOTIFY_EMAIL', 'true').lower() == 'true'
    DRY_RUN_MODE = os.getenv('DRY_RUN_MODE', 'false').lower() == 'true'
    
    # OAuth Scopes
    YOUTUBE_SCOPES = [
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.force-ssl',
        'https://www.googleapis.com/auth/yt-analytics.readonly',
        'https://www.googleapis.com/auth/youtube.readonly',
    ]
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return missing required fields."""
        missing = []
        warnings = []
        
        # Required for YouTube API
        if not cls.YOUTUBE_CLIENT_ID:
            missing.append('YOUTUBE_CLIENT_ID')
        if not cls.YOUTUBE_CLIENT_SECRET:
            missing.append('YOUTUBE_CLIENT_SECRET')
        
        # Required for AI generation
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY and not cls.GOOGLE_AI_API_KEY:
            missing.append('OPENAI_API_KEY or ANTHROPIC_API_KEY or GOOGLE_AI_API_KEY')
        
        # Optional warnings
        if not cls.SLACK_WEBHOOK_URL and not cls.EMAIL_FROM:
            warnings.append('No notification method configured (Slack or Email)')
        
        return {
            'valid': len(missing) == 0,
            'missing': missing,
            'warnings': warnings,
        }
    
    @classmethod
    def get_llm_provider(cls) -> str:
        """Determine which LLM provider to use."""
        # Check for valid API keys (not placeholder values)
        valid_openai = cls.OPENAI_API_KEY and not cls.OPENAI_API_KEY.startswith('your_')
        valid_anthropic = cls.ANTHROPIC_API_KEY and not cls.ANTHROPIC_API_KEY.startswith('your_')
        valid_google = cls.GOOGLE_AI_API_KEY and cls.GOOGLE_AI_API_KEY.startswith('AIza')
        
        if valid_openai:
            return 'openai'
        elif valid_anthropic:
            return 'anthropic'
        elif valid_google:
            return 'google'
        else:
            raise ValueError("No LLM API key configured")
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            'openai_model': cls.OPENAI_MODEL,
            'anthropic_model': cls.ANTHROPIC_MODEL,
            'database_url': cls.DATABASE_URL.split('://')[0] + '://***',  # Hide connection string
            'log_level': cls.LOG_LEVEL,
            'max_retries': cls.MAX_RETRIES,
            'batch_size': cls.BATCH_SIZE,
            'default_language': cls.DEFAULT_LANGUAGE,
            'max_title_length': cls.MAX_TITLE_LENGTH,
            'max_description_length': cls.MAX_DESCRIPTION_LENGTH,
            'max_tags_length': cls.MAX_TAGS_LENGTH,
            'enable_auto_rollback': cls.ENABLE_AUTO_ROLLBACK,
            'enable_scheduled_reoptimization': cls.ENABLE_SCHEDULED_REOPTIMIZATION,
            'enable_asr_fallback': cls.ENABLE_ASR_FALLBACK,
            'dry_run_mode': cls.DRY_RUN_MODE,
            'guardrail_ctr_drop_threshold': cls.GUARDRAIL_CTR_DROP_THRESHOLD,
            'guardrail_check_days': cls.GUARDRAIL_CHECK_DAYS,
        }
