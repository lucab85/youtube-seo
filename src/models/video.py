"""Video model for storing current YouTube video metadata."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, func
from .base import Base


class Video(Base):
    """Represents a YouTube video with current metadata."""
    
    __tablename__ = 'videos'
    
    video_id = Column(String(20), primary_key=True, index=True)
    channel_id = Column(String(30), nullable=False, index=True)
    
    # Current metadata
    title_current = Column(String(100), nullable=True)
    description_current = Column(Text, nullable=True)
    tags_current = Column(String(500), nullable=True)
    
    # Additional info
    lang = Column(String(10), default='en')
    category_id = Column(String(10), nullable=True)
    
    # Scheduled publishing
    planned_publish_at_utc = Column(DateTime, nullable=True)
    planned_publish_at_tz = Column(String(50), nullable=True)
    planned_publish_at_local = Column(String(100), nullable=True)
    
    # Monetization fields
    monetization_enabled_intent = Column(Boolean, nullable=True)
    monetization_ad_suitability = Column(String(20), nullable=True)  # standard|limited|mature|not_sure
    monetization_ad_formats = Column(String(200), nullable=True)  # CSV: skippable,overlay,etc
    monetization_paid_promotion = Column(String(20), nullable=True)  # none|includes|not_sure
    monetization_made_for_kids = Column(Boolean, nullable=True)
    monetization_age_restriction = Column(String(20), nullable=True)  # none|18+|unknown
    monetization_notes = Column(Text, nullable=True)
    monetization_api_applied = Column(Boolean, nullable=True)  # any programmatic change made
    monetization_completion_state = Column(String(20), nullable=True)  # APPLIED|PARTIAL|REQUIRES_STUDIO|SKIPPED
    monetization_studio_deeplink = Column(String(500), nullable=True)
    monetization_last_attempt_at_utc = Column(DateTime, nullable=True)
    
    # Timestamps
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Video(video_id='{self.video_id}', title='{self.title_current[:30]}...')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'title': self.title_current,
            'description': self.description_current,
            'tags': self.tags_current,
            'lang': self.lang,
            'category_id': self.category_id,
            'planned_publish_at_utc': self.planned_publish_at_utc.isoformat() if self.planned_publish_at_utc else None,
            'planned_publish_at_tz': self.planned_publish_at_tz,
            'planned_publish_at_local': self.planned_publish_at_local,
            'monetization_enabled_intent': self.monetization_enabled_intent,
            'monetization_completion_state': self.monetization_completion_state,
            'monetization_studio_deeplink': self.monetization_studio_deeplink,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
