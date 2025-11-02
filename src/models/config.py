"""Config model for storing user/channel-specific settings."""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from .base import Base


class Config(Base):
    """Represents user/channel configuration for SEO generation."""
    
    __tablename__ = 'configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    channel_id = Column(String(30), nullable=True, index=True)
    
    # Configuration JSON blobs
    policy_json = Column(JSON, nullable=True)  # Prohibited terms, required disclosures
    brand_json = Column(JSON, nullable=True)  # Tone, style, CTAs, brand voice
    notification_json = Column(JSON, nullable=True)  # Slack webhook, email addresses
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Config(id={self.id}, user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'policy': self.policy_json,
            'brand': self.brand_json,
            'notification': self.notification_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @staticmethod
    def get_default_policy():
        """Get default policy configuration."""
        return {
            'prohibited_terms': [],
            'required_disclosures': [],
            'coppa_compliant': True,
        }
    
    @staticmethod
    def get_default_brand():
        """Get default brand configuration."""
        return {
            'tone': 'professional',
            'style': 'educational',
            'brand_keywords': [],
            'cta_template': 'Subscribe for more content!',
            'allow_emojis': False,
        }
    
    @staticmethod
    def get_default_notification():
        """Get default notification configuration."""
        return {
            'slack_enabled': False,
            'email_enabled': False,
            'notify_on_success': True,
            'notify_on_failure': True,
            'notify_on_rollback': True,
        }
