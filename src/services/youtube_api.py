"""YouTube API client wrapper for authentication and API calls."""

import os
import json
from typing import Dict, List, Optional, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger('youtube_api')


class YouTubeAPIClient:
    """Client for YouTube Data API v3 and YouTube Analytics API."""
    
    def __init__(self):
        """Initialize YouTube API client."""
        self.credentials: Optional[Credentials] = None
        self.youtube = None
        self.analytics = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        token_file = Config.OAUTH_TOKEN_FILE
        credentials_file = Config.OAUTH_CREDENTIALS_FILE
        
        # Check if token file exists
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                    self.credentials = Credentials.from_authorized_user_info(
                        token_data,
                        Config.YOUTUBE_SCOPES
                    )
                logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load token file: {e}")
                self.credentials = None
        
        # Refresh or obtain new credentials
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    self.credentials = None
            
            # Run OAuth flow if no valid credentials
            if not self.credentials:
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(
                        f"OAuth credentials file not found: {credentials_file}\n"
                        "Please download client_secrets.json from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file,
                    Config.YOUTUBE_SCOPES
                )
                self.credentials = flow.run_local_server(port=0)
                logger.info("Completed OAuth flow")
            
            # Save credentials
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, 'w') as f:
                f.write(self.credentials.to_json())
            logger.info(f"Saved credentials to {token_file}")
        
        # Build API clients
        self.youtube = build('youtube', 'v3', credentials=self.credentials)
        self.analytics = build('youtubeAnalytics', 'v2', credentials=self.credentials)
        logger.info("YouTube API clients initialized")
    
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video details from YouTube.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Video details dict or None if error
        """
        try:
            response = self.youtube.videos().list(
                part='snippet,contentDetails,status',
                id=video_id
            ).execute()
            
            if response.get('items'):
                video = response['items'][0]
                logger.info(f"Retrieved video details for {video_id}")
                return video
            else:
                logger.warning(f"Video not found: {video_id}")
                return None
        
        except HttpError as e:
            logger.error(f"HTTP error getting video details: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting video details: {e}")
            return None
    
    def update_video_metadata(
        self,
        video_id: str,
        title: str,
        description: str,
        tags: List[str],
        category_id: Optional[str] = None
    ) -> bool:
        """
        Update video metadata on YouTube.
        
        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: List of tags
            category_id: Video category ID (preserve existing if None)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current video details to preserve other fields
            current_video = self.get_video_details(video_id)
            if not current_video:
                logger.error(f"Cannot update - video not found: {video_id}")
                return False
            
            # Prepare update body
            snippet = current_video['snippet']
            snippet['title'] = title
            snippet['description'] = description
            snippet['tags'] = tags
            
            if category_id:
                snippet['categoryId'] = category_id
            
            # Debug: Log description and tags
            logger.info(f"Updating video {video_id}")
            logger.info(f"Description has {description.count(chr(10))} newline characters")
            logger.info(f"First 200 chars with repr: {repr(description[:200])}")
            logger.info(f"Number of tags: {len(tags)}")
            logger.info(f"Tags: {tags}")
            
            # Update video
            response = self.youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            ).execute()
            
            logger.info(f"Successfully updated video metadata: {video_id}")
            return True
        
        except HttpError as e:
            logger.error(f"HTTP error updating video: {e}")
            if e.resp.status == 403:
                logger.error("Permission denied - check OAuth scopes and video ownership")
            elif e.resp.status == 429:
                logger.error("Rate limit exceeded - implement backoff")
            return False
        except Exception as e:
            logger.error(f"Error updating video: {e}")
            return False
    
    def enable_monetization(self, video_id: str, license_type: str = 'youtube') -> bool:
        """
        Enable monetization for a video (sets up prerequisites).
        
        Args:
            video_id: YouTube video ID
            license_type: 'youtube' (standard) or 'creativeCommon'
        
        Returns:
            True if successful, False otherwise
        
        Note:
            IMPORTANT LIMITATIONS:
            - YouTube Data API v3 does NOT support full monetization control
            - This method only sets video as eligible (not made for kids, proper license)
            - Actual monetization (ad types, etc.) must be enabled via:
              1. YouTube Studio (manual)
              2. Channel-level default monetization settings (applies to new uploads)
              3. YouTube Content Manager API (for partners only)
            
            WORKAROUND FOR AUTOMATION:
            If you want automatic monetization for ALL new videos:
            1. Go to YouTube Studio > Monetization > Default settings
            2. Enable monetization and select ad types as defaults
            3. All future uploads will inherit these settings automatically
        """
        try:
            # Get current video details
            current_video = self.get_video_details(video_id)
            if not current_video:
                logger.error(f"Cannot enable monetization - video not found: {video_id}")
                return False
            
            # Check current status
            current_status = current_video.get('status', {})
            
            # Prepare updated status
            updated_status = {
                'id': video_id,
                'status': {
                    'privacyStatus': current_status.get('privacyStatus', 'public'),
                    'madeForKids': False,  # Required for monetization
                    'selfDeclaredMadeForKids': False,
                    'license': license_type,  # 'youtube' allows monetization
                    'embeddable': current_status.get('embeddable', True),
                    'publicStatsViewable': current_status.get('publicStatsViewable', True)
                }
            }
            
            # Update video status
            response = self.youtube.videos().update(
                part='status',
                body=updated_status
            ).execute()
            
            logger.info(f"Updated video status for monetization eligibility: {video_id}")
            logger.info(f"Video is now eligible for monetization (not made for kids, license: {license_type})")
            logger.warning("")
            logger.warning("⚠️  IMPORTANT: YouTube API v3 does NOT support automatic monetization activation")
            logger.warning("")
            logger.warning("To enable monetization automatically for ALL future videos:")
            logger.warning("1. Go to YouTube Studio: https://studio.youtube.com")
            logger.warning("2. Click Settings (bottom left) > Upload defaults")
            logger.warning("3. Go to 'Advanced settings' tab")
            logger.warning("4. Set 'Standard YouTube License'")
            logger.warning("5. Go to 'Monetization' section in left menu")
            logger.warning("6. Enable monetization and select ad types as defaults")
            logger.warning("7. All new uploads will automatically use these monetization settings")
            logger.warning("")
            logger.warning("For THIS specific video, manually enable monetization:")
            logger.warning("- Go to: https://studio.youtube.com/video/{}/monetization".format(video_id))
            logger.warning("- Click 'ON' and select ad types")
            
            return True
        
        except HttpError as e:
            logger.error(f"HTTP error enabling monetization: {e}")
            if e.resp.status == 403:
                logger.error("Permission denied - channel may not be in YouTube Partner Program")
            elif e.resp.status == 400:
                logger.error("Bad request - check if channel is monetization-eligible")
            return False
        except Exception as e:
            logger.error(f"Error enabling monetization: {e}")
            return False
    
    def check_monetization_status(self, video_id: str) -> Dict[str, Any]:
        """
        Check the monetization status and eligibility of a video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Dict with monetization information
        """
        try:
            video = self.get_video_details(video_id)
            if not video:
                return {'error': 'Video not found'}
            
            status = video.get('status', {})
            
            # Check eligibility factors
            made_for_kids = status.get('madeForKids', False)
            license_type = status.get('license', 'unknown')
            privacy = status.get('privacyStatus', 'unknown')
            
            eligible = not made_for_kids and license_type == 'youtube' and privacy == 'public'
            
            return {
                'video_id': video_id,
                'eligible_for_monetization': eligible,
                'made_for_kids': made_for_kids,
                'license': license_type,
                'privacy': privacy,
                'note': 'Actual monetization status (ads enabled) cannot be read via API v3'
            }
        
        except Exception as e:
            logger.error(f"Error checking monetization status: {e}")
            return {'error': str(e)}
    
    def list_captions(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        List available captions for a video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            List of caption tracks or None if error
        """
        try:
            response = self.youtube.captions().list(
                part='snippet',
                videoId=video_id
            ).execute()
            
            captions = response.get('items', [])
            logger.info(f"Found {len(captions)} caption tracks for {video_id}")
            return captions
        
        except HttpError as e:
            logger.error(f"HTTP error listing captions: {e}")
            return None
        except Exception as e:
            logger.error(f"Error listing captions: {e}")
            return None
    
    def download_caption(self, caption_id: str) -> Optional[str]:
        """
        Download caption/transcript content.
        
        Args:
            caption_id: Caption track ID
        
        Returns:
            Caption text or None if error
        """
        try:
            caption_content = self.youtube.captions().download(
                id=caption_id,
                tfmt='srt'  # SubRip format
            ).execute()
            
            logger.info(f"Downloaded caption: {caption_id}")
            return caption_content.decode('utf-8') if isinstance(caption_content, bytes) else caption_content
        
        except HttpError as e:
            logger.error(f"HTTP error downloading caption: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading caption: {e}")
            return None
    
    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[str]:
        """
        Get list of video IDs from a channel.
        
        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to retrieve
        
        Returns:
            List of video IDs
        """
        try:
            # Get uploads playlist ID
            response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not response.get('items'):
                logger.warning(f"Channel not found: {channel_id}")
                return []
            
            uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist
            video_ids = []
            next_page_token = None
            
            while len(video_ids) < max_results:
                playlist_response = self.youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(video_ids)),
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_response.get('items', []):
                    video_ids.append(item['contentDetails']['videoId'])
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            logger.info(f"Retrieved {len(video_ids)} videos from channel {channel_id}")
            return video_ids
        
        except HttpError as e:
            logger.error(f"HTTP error getting channel videos: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            return []
    
    def check_video_ownership(self, video_id: str) -> bool:
        """
        Check if authenticated user owns/can edit the video.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            True if user has permission to edit
        """
        try:
            video = self.get_video_details(video_id)
            if not video:
                return False
            
            # If we can retrieve the video with full snippet, we likely have access
            # A more robust check would be to attempt a no-op update
            return True
        
        except Exception as e:
            logger.error(f"Error checking ownership: {e}")
            return False
    
    def retry_with_backoff(self, func, max_retries: int = 3, *args, **kwargs):
        """
        Retry API call with exponential backoff.
        
        Args:
            func: Function to call
            max_retries: Maximum number of retries
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result or None if all retries failed
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    wait_time = (2 ** attempt) * Config.RETRY_DELAY
                    logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = (2 ** attempt) * Config.RETRY_DELAY
                logger.warning(f"Error on attempt {attempt + 1}/{max_retries}, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        return None
