"""Job model for tracking background tasks and batch operations."""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from .base import Base


class Job(Base):
    """Represents a job (generation, publish, re-optimization, etc.)."""
    
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Job metadata
    type = Column(String(50), nullable=False, index=True)  # 'generate', 'publish', 'reoptimize', 'rollback'
    status = Column(String(20), nullable=False, index=True, default='pending')  # 'pending', 'running', 'completed', 'failed'
    
    # Input/output data (JSON)
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<Job(id={self.id}, type='{self.type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'type': self.type,
            'status': self.status,
            'input': self.input_json,
            'output': self.output_json,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
