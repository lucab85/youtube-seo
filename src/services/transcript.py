"""Transcript extraction service with multiple fallback methods."""

import re
from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger('transcript')


class TranscriptService:
    """Service for extracting video transcripts with fallback methods."""
    
    def __init__(self, youtube_client=None):
        """
        Initialize transcript service.
        
        Args:
            youtube_client: YouTubeAPIClient instance (optional)
        """
        self.youtube_client = youtube_client
    
    def get_transcript(
        self,
        video_id: str,
        language: str = 'en',
        fallback_to_auto: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get transcript for a video using multiple fallback methods.
        
        Args:
            video_id: YouTube video ID
            language: Preferred language code
            fallback_to_auto: Whether to fall back to auto-generated captions
        
        Returns:
            Dict with 'text', 'language', 'method' keys, or None if failed
        """
        logger.info(f"Fetching transcript for video {video_id}")
        
        # Method 1: Try Captions API if YouTube client available
        if self.youtube_client:
            transcript = self._get_via_captions_api(video_id, language)
            if transcript:
                return transcript
        
        # Method 2: Try youtube_transcript_api library
        transcript = self._get_via_transcript_api(video_id, language, fallback_to_auto)
        if transcript:
            return transcript
        
        # Method 3: ASR fallback (if enabled)
        if Config.ENABLE_ASR_FALLBACK:
            transcript = self._get_via_asr(video_id)
            if transcript:
                return transcript
        
        logger.error(f"All transcript methods failed for video {video_id}")
        return None
    
    def _get_via_captions_api(
        self,
        video_id: str,
        language: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get transcript via YouTube Captions API (for owned videos).
        
        Args:
            video_id: YouTube video ID
            language: Preferred language code
        
        Returns:
            Transcript dict or None
        """
        try:
            if not self.youtube_client:
                return None
            
            # List available captions
            captions = self.youtube_client.list_captions(video_id)
            if not captions:
                logger.info(f"No captions found via Captions API for {video_id}")
                return None
            
            # Find caption track matching language
            target_caption = None
            for caption in captions:
                lang = caption['snippet']['language']
                if lang == language:
                    target_caption = caption
                    break
            
            # Fallback to first available caption
            if not target_caption and captions:
                target_caption = captions[0]
                logger.info(f"Using fallback language: {target_caption['snippet']['language']}")
            
            if target_caption:
                caption_id = target_caption['id']
                caption_text = self.youtube_client.download_caption(caption_id)
                
                if caption_text:
                    # Clean SRT format
                    cleaned_text = self._clean_srt_format(caption_text)
                    
                    return {
                        'text': cleaned_text,
                        'language': target_caption['snippet']['language'],
                        'method': 'captions_api',
                        'is_auto_generated': target_caption['snippet'].get('trackKind') == 'asr'
                    }
        
        except Exception as e:
            logger.warning(f"Captions API method failed: {e}")
        
        return None
    
    def _get_via_transcript_api(
        self,
        video_id: str,
        language: str,
        fallback_to_auto: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Get transcript via youtube_transcript_api library.
        
        Args:
            video_id: YouTube video ID
            language: Preferred language code
            fallback_to_auto: Whether to use auto-generated captions
        
        Returns:
            Transcript dict or None
        """
        try:
            # Try to get transcript in preferred language
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=[language]
            )
            
            # Combine all transcript segments
            full_text = ' '.join([entry['text'] for entry in transcript_list])
            
            logger.info(f"Retrieved transcript via transcript_api for {video_id}")
            
            return {
                'text': full_text,
                'language': language,
                'method': 'transcript_api',
                'is_auto_generated': False  # Assume manual unless we can check
            }
        
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            if fallback_to_auto:
                try:
                    # Try auto-generated captions
                    transcript_list = YouTubeTranscriptApi.get_transcript(
                        video_id,
                        languages=[language, 'en']  # Fallback to English
                    )
                    
                    full_text = ' '.join([entry['text'] for entry in transcript_list])
                    
                    logger.info(f"Retrieved auto-generated transcript for {video_id}")
                    
                    return {
                        'text': full_text,
                        'language': language,
                        'method': 'transcript_api_auto',
                        'is_auto_generated': True
                    }
                
                except Exception as auto_error:
                    logger.warning(f"Auto-generated transcript also failed: {auto_error}")
            else:
                logger.warning(f"Transcript not available: {e}")
        
        except VideoUnavailable:
            logger.error(f"Video unavailable: {video_id}")
        
        except Exception as e:
            logger.warning(f"transcript_api method failed: {e}")
        
        return None
    
    def _get_via_asr(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transcript via ASR (Automatic Speech Recognition).
        
        This is a placeholder for ASR integration (Whisper, Google Speech-to-Text, etc.)
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Transcript dict or None
        """
        logger.warning("ASR fallback not yet implemented")
        # TODO: Implement ASR using Whisper or similar
        # 1. Download audio using yt-dlp or pytube
        # 2. Run through ASR model
        # 3. Return transcript
        return None
    
    def _clean_srt_format(self, srt_text: str) -> str:
        """
        Clean SRT subtitle format to plain text.
        
        Args:
            srt_text: Raw SRT formatted text
        
        Returns:
            Cleaned plain text
        """
        # Remove timestamp lines (e.g., "00:00:01,234 --> 00:00:04,567")
        text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', '', srt_text)
        
        # Remove sequence numbers
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def clean_transcript(self, text: str, remove_filler: bool = True) -> str:
        """
        Clean and normalize transcript text.
        
        Args:
            text: Raw transcript text
            remove_filler: Whether to remove filler words
        
        Returns:
            Cleaned text
        """
        # Remove music notes and sound effects
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove filler words if requested
        if remove_filler:
            filler_words = [
                r'\buh\b', r'\bum\b', r'\blike\b(?!\s+to\b)',
                r'\byou know\b', r'\bkinda\b', r'\bsorta\b'
            ]
            for filler in filler_words:
                text = re.sub(filler, '', text, flags=re.IGNORECASE)
        
        # Clean up punctuation
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        
        # Normalize whitespace again
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_timestamps(self, video_id: str) -> Optional[list]:
        """
        Extract timestamps/chapters from transcript.
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            List of timestamp dicts or None
        """
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Look for chapter-like patterns (significant pauses, topic changes)
            # This is a simplified implementation
            timestamps = []
            
            for i, entry in enumerate(transcript_list):
                text = entry['text'].lower()
                
                # Look for chapter indicators
                if any(keyword in text for keyword in ['chapter', 'section', 'part', 'intro', 'conclusion']):
                    timestamps.append({
                        'time': entry['start'],
                        'text': entry['text'],
                        'duration': entry['duration']
                    })
            
            return timestamps if timestamps else None
        
        except Exception as e:
            logger.warning(f"Failed to extract timestamps: {e}")
            return None
