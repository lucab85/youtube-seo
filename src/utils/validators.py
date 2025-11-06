"""Input validation and data sanitization utilities."""

import re
from typing import Dict, Optional, Tuple, NamedTuple
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dateutil import parser as dateutil_parser
from .config import Config
from .logger import get_logger

logger = get_logger('validators')


class PublishAt(NamedTuple):
    """Parsed and validated publication datetime."""
    utc: datetime  # UTC datetime object
    tz: str  # IANA timezone name
    local: datetime  # Local datetime with timezone
    utc_rfc3339: str  # RFC3339 formatted string for API
    local_display: str  # Human-readable local time


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
    Remove all hashtags from text while preserving line breaks.
    
    Args:
        text: Input text that may contain hashtags
    
    Returns:
        Text with hashtags removed but line breaks preserved
    """
    # Remove hashtags (# followed by word characters)
    text = re.sub(r'#\w+', '', text)
    
    # Remove standalone # characters
    text = text.replace('#', '')
    
    # Clean up extra spaces on each line (but preserve newlines)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Collapse multiple spaces to single space within each line
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned_lines.append(cleaned_line)
    
    # Rejoin with newlines
    text = '\n'.join(cleaned_lines)
    
    # Remove any excessive blank lines (more than 2 consecutive newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


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
    Parse and sanitize tags from various input formats.
    
    Args:
        tags_input: Tags as comma-separated string
    
    Returns:
        List of individual sanitized tags (max 30 tags per YouTube limits)
    
    Note:
        YouTube tags can only contain: letters, numbers, spaces, hyphens
        Any other characters will cause API errors
        YouTube also has a combined character limit of ~400 chars for all tags
    """
    from .config import Config
    
    # Split by comma
    tags = [tag.strip() for tag in tags_input.split(',')]
    
    # Remove empty tags and sanitize
    sanitized_tags = []
    for tag in tags:
        if not tag:
            continue
        
        # YouTube is very strict about tag characters
        # Only allow: alphanumeric, spaces, hyphens
        # Remove ALL other characters including special chars and punctuation
        tag = re.sub(r'[^a-zA-Z0-9\s-]', '', tag)
        
        # Clean up multiple spaces and hyphens
        tag = re.sub(r'\s+', ' ', tag)
        tag = re.sub(r'-+', '-', tag)
        tag = tag.strip().strip('-')
        
        # Ensure tag is not too long (YouTube max is 30 chars per tag)
        if len(tag) > 30:
            # Truncate at word boundary
            tag = tag[:30].rstrip()
            # Remove trailing hyphen if any
            tag = tag.rstrip('-')
        
        # Skip if tag becomes empty after sanitization or is too short
        if tag and len(tag) >= 2:
            sanitized_tags.append(tag)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    total_length = 0
    max_total_length = Config.MAX_TAGS_LENGTH
    
    for tag in sanitized_tags:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            # Calculate length with comma separator (except for first tag)
            tag_length = len(tag) + (2 if unique_tags else 0)  # +2 for ", "
            
            # Check if adding this tag would exceed total character limit
            if total_length + tag_length > max_total_length:
                logger.warning(f"Reached total tag character limit ({max_total_length}), stopping at {len(unique_tags)} tags")
                break
            
            # Check if we've reached the maximum number of tags
            if len(unique_tags) >= 30:
                logger.warning(f"Reached maximum tag count (30)")
                break
            
            seen.add(tag_lower)
            unique_tags.append(tag)
            total_length += tag_length
    
    if len(sanitized_tags) > len(unique_tags):
        logger.info(f"Filtered tags from {len(sanitized_tags)} to {len(unique_tags)} (total {total_length} chars)")
    
    return unique_tags


def parse_publish_at(dt_str: str, tz_hint: Optional[str] = None) -> PublishAt:
    """
    Parse and validate publication datetime with timezone handling.
    
    Args:
        dt_str: Datetime string in various formats (ISO 8601, natural language, etc.)
        tz_hint: Optional IANA timezone hint if dt_str lacks timezone info
    
    Returns:
        PublishAt object with normalized UTC and local times
    
    Raises:
        ValueError: If datetime is invalid, in the past, or timezone is ambiguous
    
    Examples:
        >>> parse_publish_at("2025-11-10T14:00:00+01:00")
        >>> parse_publish_at("2025-11-10 14:00", tz_hint="Europe/Amsterdam")
        >>> parse_publish_at("Nov 10, 2025 2pm CET")
    """
    import tzlocal
    
    if not dt_str or not dt_str.strip():
        raise ValueError(
            "Invalid --publish-at value. Try ISO 8601 (e.g., 2025-11-10T14:00:00+01:00) or supply --tz Europe/Amsterdam."
        )
    
    dt_str = dt_str.strip()
    parsed_dt = None
    tz_name = None
    
    # Try to parse the datetime string
    try:
        # First, try dateutil parser which handles many formats
        parsed_dt = dateutil_parser.parse(dt_str, fuzzy=False)
        
        # Check if timezone info is present
        if parsed_dt.tzinfo is None:
            # No timezone in string, need to use hint or system default
            if tz_hint:
                # Validate IANA timezone
                try:
                    tz = ZoneInfo(tz_hint)
                    tz_name = tz_hint
                except ZoneInfoNotFoundError:
                    raise ValueError(
                        f"--tz must be a valid IANA timezone (e.g., Europe/Amsterdam). Got: {tz_hint}"
                    )
                
                # Check for DST ambiguity
                try:
                    parsed_dt = parsed_dt.replace(tzinfo=tz)
                except Exception as e:
                    if "ambiguous" in str(e).lower():
                        raise ValueError(
                            "Ambiguous local time due to DST. Specify an explicit offset (e.g., +02:00) or an IANA timezone."
                        )
                    raise
            else:
                # Use system local timezone and warn
                try:
                    local_tz = tzlocal.get_localzone()
                    tz_name = str(local_tz)
                    parsed_dt = parsed_dt.replace(tzinfo=local_tz)
                    logger.warning(
                        f"No timezone specified in --publish-at. Using system timezone: {tz_name}"
                    )
                except Exception as e:
                    raise ValueError(
                        "Invalid --publish-at value. Try ISO 8601 (e.g., 2025-11-10T14:00:00+01:00) or supply --tz Europe/Amsterdam."
                    )
        else:
            # Timezone is in the string, extract the name
            if hasattr(parsed_dt.tzinfo, 'key'):
                tz_name = parsed_dt.tzinfo.key
            elif hasattr(parsed_dt.tzinfo, 'zone'):
                tz_name = parsed_dt.tzinfo.zone
            else:
                # For fixed offsets, create a descriptive name
                offset = parsed_dt.utcoffset()
                if offset:
                    hours = int(offset.total_seconds() // 3600)
                    minutes = int((offset.total_seconds() % 3600) // 60)
                    tz_name = f"UTC{hours:+03d}:{minutes:02d}"
                else:
                    tz_name = "UTC"
    
    except (ValueError, TypeError, OverflowError) as e:
        error_msg = str(e)
        if "ambiguous" in error_msg.lower():
            raise ValueError(
                "Ambiguous local time due to DST. Specify an explicit offset (e.g., +02:00) or an IANA timezone."
            )
        raise ValueError(
            f"Invalid --publish-at value. Try ISO 8601 (e.g., 2025-11-10T14:00:00+01:00) or supply --tz Europe/Amsterdam. Error: {error_msg}"
        )
    
    if not parsed_dt:
        raise ValueError(
            "Invalid --publish-at value. Try ISO 8601 (e.g., 2025-11-10T14:00:00+01:00) or supply --tz Europe/Amsterdam."
        )
    
    # Convert to UTC for validation
    utc_dt = parsed_dt.astimezone(timezone.utc)
    now_utc = datetime.now(timezone.utc)
    
    # Enforce future-time rule (at least 5 minutes in the future)
    min_future = now_utc + timedelta(minutes=5)
    if utc_dt < min_future:
        raise ValueError(
            "--publish-at must be at least 5 minutes in the future."
        )
    
    # Format RFC3339 for YouTube API
    utc_rfc3339 = utc_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    # Create human-readable local display
    local_display = parsed_dt.strftime('%Y-%m-%d %H:%M %Z')
    if not local_display.endswith(tz_name):
        local_display = f"{parsed_dt.strftime('%Y-%m-%d %H:%M')} {tz_name}"
    
    logger.info(
        f"Parsed publish time: {local_display} (UTC: {utc_rfc3339})"
    )
    
    return PublishAt(
        utc=utc_dt,
        tz=tz_name,
        local=parsed_dt,
        utc_rfc3339=utc_rfc3339,
        local_display=local_display
    )



def format_tags_output(tags: list) -> str:
    """
    Format tags list as comma-separated string.
    
    Args:
        tags: List of tags
    
    Returns:
        Comma-separated tag string
    """
    return ', '.join(tags)


def validate_ad_suitability(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate ad suitability enum value.
    
    Args:
        value: Ad suitability string
    
    Returns:
        Tuple of (is_valid, normalized_value or error_message)
    """
    valid_values = ['standard', 'limited', 'mature', 'not_sure']
    normalized = value.lower().strip()
    
    if normalized in valid_values:
        return True, normalized
    else:
        return False, f"Invalid ad suitability: '{value}'. Must be one of: {', '.join(valid_values)}"


def validate_paid_promotion(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate paid promotion enum value.
    
    Args:
        value: Paid promotion string
    
    Returns:
        Tuple of (is_valid, normalized_value or error_message)
    """
    valid_values = ['none', 'includes', 'not_sure']
    normalized = value.lower().strip()
    
    if normalized in valid_values:
        return True, normalized
    else:
        return False, f"Invalid paid promotion: '{value}'. Must be one of: {', '.join(valid_values)}"


def validate_age_restriction(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate age restriction enum value.
    
    Args:
        value: Age restriction string
    
    Returns:
        Tuple of (is_valid, normalized_value or error_message)
    """
    valid_values = ['none', '18+']
    normalized = value.lower().strip()
    
    if normalized in valid_values:
        return True, normalized
    else:
        return False, f"Invalid age restriction: '{value}'. Must be one of: {', '.join(valid_values)}"


def validate_ad_formats(value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and normalize ad formats CSV string.
    
    Args:
        value: Comma-separated ad formats
    
    Returns:
        Tuple of (is_valid, normalized_csv or error_message)
    """
    valid_formats = ['skippable', 'non_skippable', 'overlay', 'display', 'bumper', 'mid_roll']
    
    # Parse CSV
    formats = [f.strip().lower() for f in value.split(',')]
    
    # Validate each format
    invalid = [f for f in formats if f not in valid_formats]
    
    if invalid:
        return False, f"Invalid ad format(s): {', '.join(invalid)}. Valid: {', '.join(valid_formats)}"
    
    # Return normalized CSV
    return True, ','.join(formats)

