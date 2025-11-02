"""Metadata version model for tracking changes to video metadata."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from .base import Base


class MetadataVersion(Base):
    """Represents a version of video metadata (for audit trail and rollback)."""
    
    __tablename__ = 'metadata_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String(20), ForeignKey('videos.video_id'), nullable=False, index=True)
    
    # Metadata snapshot
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(String(500), nullable=False)
    
    # Change tracking
    created_at = Column(DateTime, server_default=func.now(), index=True)
    created_by = Column(String(100), nullable=False)  # Username or 'automation'
    reason = Column(String(255), nullable=True)  # 'manual', 'scheduled', 'performance_trigger'
    
    # Performance baseline at time of change (JSON)
    performance_baseline_json = Column(JSON, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<MetadataVersion(id={self.id}, video_id='{self.video_id}', created_at='{self.created_at}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'reason': self.reason,
            'performance_baseline': self.performance_baseline_json,
            'notes': self.notes,
        }
