"""YouTube video upload service."""

import os
import time
import random
import http.client
import httplib2
from typing import Dict, Optional, Any, Callable
from pathlib import Path

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger('uploader')

# Retry configuration
MAX_RETRIES = 10
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Video categories (common ones)
VIDEO_CATEGORIES = {
    'film': '1',
    'autos': '2',
    'music': '10',
    'pets': '15',
    'sports': '17',
    'travel': '19',
    'gaming': '20',
    'vlog': '22',
    'comedy': '23',
    'entertainment': '24',
    'news': '25',
    'howto': '26',
    'education': '27',
    'science': '28',
    'nonprofit': '29',
}

# Privacy status options
PRIVACY_STATUS = ['public', 'private', 'unlisted']


class VideoUploader:
    """Service for uploading videos to YouTube."""
    
    def __init__(self, youtube_client):
        """
        Initialize video uploader.
        
        Args:
            youtube_client: YouTubeAPIClient instance
        """
        self.youtube = youtube_client.youtube
        self.credentials = youtube_client.credentials
    
    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        category: str = "education",
        privacy_status: str = "private",
        made_for_kids: bool = False,
        notify_subscribers: bool = True,
        progress_callback: Callable[[int, int], None] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a video to YouTube.
        
        Args:
            file_path: Path to the video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags
            category: Video category (e.g., 'education', 'howto', 'entertainment')
            privacy_status: 'public', 'private', or 'unlisted'
            made_for_kids: Whether the video is made for kids
            notify_subscribers: Whether to notify subscribers (only for public videos)
            progress_callback: Optional callback function(bytes_uploaded, total_bytes)
        
        Returns:
            Dict with video details including 'id' on success, None on failure
        """
        # Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"Video file not found: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        logger.info(f"Preparing to upload: {file_name} ({file_size / 1024 / 1024:.1f} MB)")
        
        # Validate title length
        if len(title) > 100:
            logger.warning(f"Title truncated from {len(title)} to 100 chars")
            title = title[:100]
        
        # Validate description length
        if len(description) > 5000:
            logger.warning(f"Description truncated from {len(description)} to 5000 chars")
            description = description[:5000]
        
        # Get category ID
        category_id = VIDEO_CATEGORIES.get(category.lower(), '27')  # Default to education
        
        # Validate privacy status
        if privacy_status not in PRIVACY_STATUS:
            logger.warning(f"Invalid privacy status '{privacy_status}', using 'private'")
            privacy_status = 'private'
        
        # Build request body
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': category_id,
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids,
            }
        }
        
        # Only notify subscribers for public videos
        if privacy_status == 'public' and notify_subscribers:
            body['status']['publishAt'] = None  # Publish immediately
        
        # Create media upload object with resumable upload
        media = MediaFileUpload(
            file_path,
            mimetype='video/*',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )
        
        try:
            # Create the upload request
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers if privacy_status == 'public' else False
            )
            
            # Execute resumable upload with retry logic
            response = self._resumable_upload(request, file_size, progress_callback)
            
            if response:
                video_id = response.get('id')
                logger.info(f"Successfully uploaded video: {video_id}")
                logger.info(f"Title: {title}")
                logger.info(f"URL: https://www.youtube.com/watch?v={video_id}")
                return response
            
            return None
            
        except HttpError as e:
            logger.error(f"HTTP error during upload: {e}")
            if e.resp.status == 403:
                if 'quotaExceeded' in str(e):
                    logger.error("YouTube API quota exceeded")
                else:
                    logger.error("Permission denied - check OAuth scopes")
            return None
        except Exception as e:
            logger.error(f"Error during upload: {e}")
            return None
    
    def _resumable_upload(
        self,
        request,
        total_size: int,
        progress_callback: Callable[[int, int], None] = None
    ) -> Optional[Dict]:
        """
        Execute resumable upload with retry logic.
        
        Args:
            request: The upload request
            total_size: Total file size in bytes
            progress_callback: Optional progress callback
        
        Returns:
            Response dict on success, None on failure
        """
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                logger.info("Uploading file...")
                status, response = request.next_chunk()
                
                if status:
                    progress = int(status.progress() * 100)
                    bytes_uploaded = int(status.resumable_progress)
                    logger.info(f"Upload progress: {progress}% ({bytes_uploaded / 1024 / 1024:.1f} MB)")
                    
                    if progress_callback:
                        progress_callback(bytes_uploaded, total_size)
                
                if response:
                    logger.info("Upload complete!")
                    return response
                    
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Retriable HTTP error {e.resp.status}: {e.content}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = f"Retriable error: {e}"
            
            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    logger.error(f"Max retries exceeded. Last error: {error}")
                    return None
                
                # Exponential backoff with jitter
                sleep_time = random.random() * (2 ** retry)
                logger.warning(f"Retry {retry}/{MAX_RETRIES} in {sleep_time:.1f}s: {error}")
                time.sleep(sleep_time)
                error = None
        
        return response
    
    def upload_with_seo(
        self,
        file_path: str,
        initial_title: str = None,
        privacy_status: str = "private",
        category: str = "education",
        process_seo: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Upload video and optionally process with SEO generator.
        
        This uploads the video first with a basic title, then can
        process it through the SEO generator if desired.
        
        Args:
            file_path: Path to video file
            initial_title: Initial title (defaults to filename)
            privacy_status: Initial privacy status
            category: Video category
            process_seo: Whether to queue for SEO processing
        
        Returns:
            Dict with upload result and video_id
        """
        # Use filename as default title
        if not initial_title:
            initial_title = Path(file_path).stem
            # Clean up common filename patterns
            initial_title = initial_title.replace('_', ' ').replace('-', ' ')
            initial_title = ' '.join(initial_title.split())  # Normalize spaces
        
        # Upload with minimal metadata
        result = self.upload_video(
            file_path=file_path,
            title=initial_title,
            description=f"Video uploaded on {time.strftime('%Y-%m-%d')}. SEO metadata pending.",
            tags=[],
            category=category,
            privacy_status=privacy_status,
            notify_subscribers=False  # Don't notify until SEO is done
        )
        
        if result:
            result['needs_seo'] = process_seo
            result['file_path'] = file_path
        
        return result


def get_video_category_id(category_name: str) -> str:
    """
    Get YouTube category ID from name.
    
    Args:
        category_name: Category name (e.g., 'education', 'howto')
    
    Returns:
        Category ID string
    """
    return VIDEO_CATEGORIES.get(category_name.lower(), '27')


def list_video_categories() -> Dict[str, str]:
    """Return available video categories."""
    return VIDEO_CATEGORIES.copy()
