"""Video publisher service for updating YouTube metadata with versioning."""

from datetime import datetime
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from ..models import Video, MetadataVersion
from ..utils.logger import get_logger
from ..utils.config import Config
from ..utils.validators import parse_tags_input

logger = get_logger('publisher')


class VideoPublisher:
    """Service for publishing/updating video metadata on YouTube."""
    
    def __init__(self, youtube_client, db_session: Session):
        """
        Initialize video publisher.
        
        Args:
            youtube_client: YouTubeAPIClient instance
            db_session: Database session
        """
        self.youtube_client = youtube_client
        self.db = db_session
    
    def publish_metadata(
        self,
        video_id: str,
        title: str,
        description: str,
        tags: str,
        created_by: str = 'automation',
        reason: str = 'auto_optimization',
        performance_baseline: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> bool:
        """
        Publish metadata to YouTube and save version to database.
        
        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: Comma-separated tags
            created_by: Username or 'automation'
            reason: Reason for update
            performance_baseline: Performance metrics at time of change
            dry_run: If True, don't actually update YouTube
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Publishing metadata for video {video_id} (dry_run={dry_run})")
        
        try:
            # Get or create video record
            video = self.db.query(Video).filter_by(video_id=video_id).first()
            
            if not video:
                # Fetch video details from YouTube
                video_details = self.youtube_client.get_video_details(video_id)
                if not video_details:
                    logger.error(f"Video not found: {video_id}")
                    return False
                
                # Create new video record
                video = Video(
                    video_id=video_id,
                    channel_id=video_details['snippet']['channelId'],
                    title_current=video_details['snippet'].get('title'),
                    description_current=video_details['snippet'].get('description'),
                    tags_current=', '.join(video_details['snippet'].get('tags', [])),
                    lang=Config.DEFAULT_LANGUAGE,
                    category_id=video_details['snippet'].get('categoryId')
                )
                self.db.add(video)
                logger.info(f"Created new video record for {video_id}")
            
            # Save previous version to history
            if video.title_current or video.description_current:
                previous_version = MetadataVersion(
                    video_id=video_id,
                    title=video.title_current or '',
                    description=video.description_current or '',
                    tags=video.tags_current or '',
                    created_by='system',
                    reason='pre_update_backup',
                    performance_baseline_json=performance_baseline
                )
                self.db.add(previous_version)
                logger.info(f"Saved previous version for {video_id}")
            
            # Parse tags to list
            tags_list = parse_tags_input(tags)
            
            # Update on YouTube (unless dry run)
            if not dry_run and not Config.DRY_RUN_MODE:
                success = self.youtube_client.update_video_metadata(
                    video_id=video_id,
                    title=title,
                    description=description,
                    tags=tags_list,
                    category_id=video.category_id
                )
                
                if not success:
                    logger.error(f"Failed to update YouTube metadata for {video_id}")
                    return False
                
                logger.info(f"Successfully updated YouTube metadata for {video_id}")
            else:
                logger.info(f"Dry run mode - skipped YouTube update for {video_id}")
            
            # Update local database
            video.title_current = title
            video.description_current = description
            video.tags_current = tags
            video.last_synced_at = datetime.utcnow()
            
            # Save new version
            new_version = MetadataVersion(
                video_id=video_id,
                title=title,
                description=description,
                tags=tags,
                created_by=created_by,
                reason=reason,
                performance_baseline_json=performance_baseline
            )
            self.db.add(new_version)
            
            # Commit transaction
            self.db.commit()
            
            logger.info(f"Successfully published metadata for {video_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error publishing metadata: {e}")
            self.db.rollback()
            return False
    
    def rollback_to_version(
        self,
        video_id: str,
        version_id: int,
        reason: str = 'manual_rollback'
    ) -> bool:
        """
        Rollback video metadata to a previous version.
        
        Args:
            video_id: YouTube video ID
            version_id: MetadataVersion ID to rollback to
            reason: Reason for rollback
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Rolling back video {video_id} to version {version_id}")
        
        try:
            # Get target version
            target_version = self.db.query(MetadataVersion).filter_by(
                id=version_id,
                video_id=video_id
            ).first()
            
            if not target_version:
                logger.error(f"Version not found: {version_id}")
                return False
            
            # Publish the old version
            success = self.publish_metadata(
                video_id=video_id,
                title=target_version.title,
                description=target_version.description,
                tags=target_version.tags,
                created_by='system',
                reason=reason
            )
            
            if success:
                logger.info(f"Successfully rolled back to version {version_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error rolling back: {e}")
            return False
    
    def get_version_history(self, video_id: str, limit: int = 10) -> list:
        """
        Get version history for a video.
        
        Args:
            video_id: YouTube video ID
            limit: Maximum number of versions to return
        
        Returns:
            List of MetadataVersion objects
        """
        try:
            versions = self.db.query(MetadataVersion).filter_by(
                video_id=video_id
            ).order_by(
                MetadataVersion.created_at.desc()
            ).limit(limit).all()
            
            return versions
        
        except Exception as e:
            logger.error(f"Error getting version history: {e}")
            return []
    
    def get_current_metadata(self, video_id: str) -> Optional[Dict[str, str]]:
        """
        Get current metadata for a video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dict with current metadata or None
        """
        try:
            video = self.db.query(Video).filter_by(video_id=video_id).first()
            
            if not video:
                # Try to fetch from YouTube
                video_details = self.youtube_client.get_video_details(video_id)
                if video_details:
                    return {
                        'title': video_details['snippet'].get('title', ''),
                        'description': video_details['snippet'].get('description', ''),
                        'tags': ', '.join(video_details['snippet'].get('tags', []))
                    }
                return None
            
            return {
                'title': video.title_current or '',
                'description': video.description_current or '',
                'tags': video.tags_current or ''
            }
        
        except Exception as e:
            logger.error(f"Error getting current metadata: {e}")
            return None
