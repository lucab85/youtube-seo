"""Input validation and data sanitization utilities."""

import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from .config import Config
from .logger import get_logger

logger = get_logger('validators')


def validate_youtube_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate YouTube URL and extract video ID.
    
    Returns:
        Tuple of (is_valid, video_id or error_message)
    """
    try:
        parsed = urlparse(url)
        
        # Standard watch URLs
        if parsed.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
            if parsed.path == '/watch':
                video_id = parse_qs(parsed.query).get('v', [None])[0]
                if video_id:
                    return True, video_id
        
        # Short URLs
        elif parsed.hostname in ['youtu.be']:
            video_id = parsed.path.lstrip('/')
            if video_id:
                return True, video_id
        
        # Embed URLs
        elif parsed.hostname in ['www.youtube.com', 'youtube.com']:
            if parsed.path.startswith('/embed/'):
                video_id = parsed.path.split('/')[2]
                if video_id:
                    return True, video_id
        
        return False, f"Invalid YouTube URL format: {url}"
    
    except Exception as e:
        return False, f"Error parsing URL: {str(e)}"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.
    
    Returns:
        Video ID or None if invalid
    """
    is_valid, result = validate_youtube_url(url)
    if is_valid:
        return result
    else:
        logger.warning(f"Failed to extract video ID: {result}")
        return None


def strip_hashtags(text: str) -> str:
    """
    Remove all hashtags from text.
    
    Args:
        text: Input text that may contain hashtags
    
    Returns:
        Text with hashtags removed
    """
    # Remove hashtags (# followed by word characters)
    text = re.sub(r'#\w+', '', text)
    
    # Remove standalone # characters
    text = text.replace('#', '')
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def enforce_character_limits(
    title: str,
    description: str,
    tags: str,
    strict: bool = True
) -> Dict[str, str]:
    """
    Enforce YouTube character limits on metadata.
    
    Args:
        title: Video title
        description: Video description
        tags: Comma-separated tags
        strict: If True, truncate; if False, raise error on overflow
    
    Returns:
        Dictionary with validated/truncated metadata
    
    Raises:
        ValueError: If strict=False and limits exceeded
    """
    max_title = Config.MAX_TITLE_LENGTH
    max_desc = Config.MAX_DESCRIPTION_LENGTH
    max_tags = Config.MAX_TAGS_LENGTH
    
    result = {}
    
    # Title
    if len(title) > max_title:
        if strict:
            # Truncate at word boundary
            result['title'] = truncate_at_word(title, max_title)
            logger.warning(f"Title truncated from {len(title)} to {len(result['title'])} chars")
        else:
            raise ValueError(f"Title exceeds {max_title} characters: {len(title)}")
    else:
        result['title'] = title
    
    # Description
    if len(description) > max_desc:
        if strict:
            result['description'] = truncate_at_word(description, max_desc)
            logger.warning(f"Description truncated from {len(description)} to {len(result['description'])} chars")
        else:
            raise ValueError(f"Description exceeds {max_desc} characters: {len(description)}")
    else:
        result['description'] = description
    
    # Tags
    if len(tags) > max_tags:
        if strict:
            result['tags'] = truncate_tags(tags, max_tags)
            logger.warning(f"Tags truncated from {len(tags)} to {len(result['tags'])} chars")
        else:
            raise ValueError(f"Tags exceed {max_tags} characters: {len(tags)}")
    else:
        result['tags'] = tags
    
    # Strip hashtags from all fields
    result['title'] = strip_hashtags(result['title'])
    result['description'] = strip_hashtags(result['description'])
    result['tags'] = strip_hashtags(result['tags'])
    
    return result


def truncate_at_word(text: str, max_length: int) -> str:
    """
    Truncate text at word boundary.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
    
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    # Reserve space for ellipsis
    if max_length > 3:
        truncated = text[:max_length - 3]
        
        # Find last space
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + '...'
    else:
        return text[:max_length]


def truncate_tags(tags: str, max_length: int) -> str:
    """
    Truncate comma-separated tags to fit within character limit.
    
    Args:
        tags: Comma-separated tags
        max_length: Maximum total character length
    
    Returns:
        Truncated tag string
    """
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    result = []
    current_length = 0
    
    for tag in tag_list:
        # Account for comma and space
        tag_length = len(tag) + (2 if result else 0)
        
        if current_length + tag_length <= max_length:
            result.append(tag)
            current_length += tag_length
        else:
            break
    
    return ', '.join(result)


def sanitize_text(text: str) -> str:
    """
    Sanitize text for safe storage and display.
    
    Args:
        text: Input text
    
    Returns:
        Sanitized text
    """
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_video_id_format(video_id: str) -> bool:
    """
    Validate video ID format (11 characters, alphanumeric with - and _).
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        True if valid format
    """
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    return bool(re.match(pattern, video_id))


def parse_tags_input(tags_input: str) -> list:
    """
    Parse tags from various input formats.
    
    Args:
        tags_input: Tags as comma-separated string
    
    Returns:
        List of individual tags (max 30 tags per YouTube limits)
    """
    # Split by comma
    tags = [tag.strip() for tag in tags_input.split(',')]
    
    # Remove empty tags
    tags = [tag for tag in tags if tag]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    # YouTube limit: maximum 30 tags
    if len(unique_tags) > 30:
        logger.warning(f"Tags limited from {len(unique_tags)} to 30 (YouTube maximum)")
        unique_tags = unique_tags[:30]
    
    return unique_tags


def format_tags_output(tags: list) -> str:
    """
    Format tags list as comma-separated string.
    
    Args:
        tags: List of tags
    
    Returns:
        Comma-separated tag string
    """
    return ', '.join(tags)
