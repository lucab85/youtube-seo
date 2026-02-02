"""Main CLI application for YouTube SEO automation."""

import argparse
import sys
import csv
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import Config
from src.utils.logger import setup_logger, get_logger
from src.utils.validators import extract_video_id, validate_video_id_format
from src.models import init_db, SessionLocal
from src.services import (
    YouTubeAPIClient,
    TranscriptService,
    SEOGenerator,
    VideoPublisher,
    AnalyticsService,
    Notifier
)
from src.services.monetization import MonetizationService

# Initialize logger
setup_logger()
logger = get_logger('main')

def validate_config():
    """Validate configuration before starting."""
    validation = Config.validate()
    
    if not validation['valid']:
        logger.error("Configuration validation failed!")
        logger.error(f"Missing required fields: {', '.join(validation['missing'])}")
        return False
    
    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(warning)
    
    logger.info("Configuration validated successfully")
    return True


def process_single_video(
    video_url: str,
    mode: str = 'auto',
    target_keywords: list = None,
    dry_run: bool = False,
    enable_monetization: bool = False,
    publish_at: dict = None,
    monetization_intent = None
) -> bool:
    """
    Process a single video.
    
    Args:
        video_url: YouTube video URL (supports watch, shorts, youtu.be, embed formats)
        mode: 'auto' (publish immediately) or 'preview' (show only)
        target_keywords: Optional list of target keywords
        dry_run: If True, don't actually update YouTube
        enable_monetization: If True, enable monetization for the video
        publish_at: Optional dict with UTC datetime, timezone, and local display
        monetization_intent: Optional MonetizationIntent object
    
    Returns:
        True if successful
    """
    # Normalize URL to canonical format and extract video ID
    try:
        from src.utils.validators import normalize_youtube_url
        video_id, canonical_url = normalize_youtube_url(video_url)
        logger.info(f"Processing video: {canonical_url} (ID: {video_id})")
    except ValueError as e:
        logger.error(f"Invalid YouTube URL: {e}")
        return False
    
    try:
        # Initialize services
        youtube_client = YouTubeAPIClient()
        transcript_service = TranscriptService(youtube_client)
        seo_generator = SEOGenerator()
        notifier = Notifier()
        
        # Get database session
        db = SessionLocal()
        publisher = VideoPublisher(youtube_client, db)
        analytics = AnalyticsService(youtube_client)
        
        # Check ownership
        if not youtube_client.check_video_ownership(video_id):
            logger.error(f"No permission to edit video: {video_id}")
            return False
        
        # Get video details
        video_details = youtube_client.get_video_details(video_id)
        if not video_details:
            logger.error(f"Could not fetch video details: {video_id}")
            return False
        
        current_title = video_details['snippet']['title']
        channel_desc = video_details['snippet'].get('channelTitle', '')
        video_duration_iso = video_details.get('contentDetails', {}).get('duration', 'PT0S')
        
        # Parse video duration
        from src.utils.validators import parse_youtube_duration, format_seconds_to_timestamp
        video_duration_seconds = parse_youtube_duration(video_duration_iso)
        video_duration_display = format_seconds_to_timestamp(video_duration_seconds)
        
        logger.info(f"Processing: {current_title}")
        logger.info(f"Video duration: {video_duration_display} ({video_duration_seconds} seconds)")
        
        # Get transcript
        transcript_data = transcript_service.get_transcript(video_id)
        if not transcript_data:
            logger.error(f"Could not fetch transcript for {video_id}")
            notifier.notify_failure(video_id, current_title, "Transcript not available")
            return False
        
        transcript_text = transcript_data['text']
        logger.info(f"Transcript retrieved: {len(transcript_text)} characters")
        
        # Clean transcript
        cleaned_transcript = transcript_service.clean_transcript(transcript_text)
        
        # Generate SEO metadata
        logger.info("Generating SEO metadata...")
        
        # Prepare context with publish_at and video duration
        generation_context = {
            'video_duration_seconds': video_duration_seconds,
            'video_duration_display': video_duration_display
        }
        if publish_at:
            generation_context['publish_at'] = publish_at
        
        metadata = seo_generator.generate_metadata(
            transcript=cleaned_transcript,
            video_title=current_title,
            channel_description=channel_desc,
            target_keywords=target_keywords,
            context=generation_context
        )
        
        # Display results
        print("\n" + "="*80)
        print("GENERATED METADATA")
        print("="*80)
        print(f"\nTitle ({len(metadata['title'])} chars):")
        print(f"  {metadata['title']}")
        print(f"\nDescription ({len(metadata['description'])} chars):")
        print(f"  {metadata['description'][:200]}...")
        print(f"\nTags ({len(metadata['tags'])} chars):")
        print(f"  {metadata['tags']}")
        print("="*80 + "\n")
        
        if mode == 'preview':
            logger.info("Preview mode - not publishing")
            return True
        
        # Get baseline metrics before update
        baseline = analytics.get_baseline_metrics(video_id, days=Config.GUARDRAIL_BASELINE_DAYS)
        
        # Publish metadata
        logger.info("Publishing metadata to YouTube...")
        success = publisher.publish_metadata(
            video_id=video_id,
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags'],
            created_by='cli_user',
            reason='manual_optimization',
            performance_baseline=baseline,
            dry_run=dry_run,
            publish_at=publish_at
        )
        
        if success:
            logger.info("✅ Successfully updated video metadata")
            
            # Try to schedule publication if publish_at is provided
            if publish_at and Config.ENABLE_YT_SCHEDULING and not dry_run:
                logger.info(f"Attempting to schedule publication for {publish_at['local']}...")
                schedule_result = publisher.schedule_publish(video_id, publish_at['utc'])
                
                if schedule_result == 'APPLIED':
                    logger.info(f"✅ Video scheduled to publish at {publish_at['local']}")
                elif schedule_result == 'SKIPPED_ALREADY_PUBLIC':
                    logger.warning(f"⚠️  Video already public - scheduling not applied (planned time stored)")
                elif schedule_result == 'FAILED_NOT_ALLOWED':
                    logger.warning(f"⚠️  YouTube API doesn't allow scheduling for this video state (planned time stored)")
                else:
                    logger.warning(f"⚠️  Scheduling failed: {schedule_result} (planned time stored)")
            
            # Process monetization if requested
            monetization_outcome = None
            if monetization_intent and monetization_intent.enable and Config.ENABLE_YT_MONETIZATION_FLOW and not dry_run:
                logger.info("Processing monetization...")
                
                # Initialize monetization service
                monetization_service = MonetizationService(youtube_client)
                
                # Apply programmatic settings
                apply_result = monetization_service.apply_programmatic_settings(video_id, monetization_intent)
                
                # Summarize outcome
                monetization_outcome = monetization_service.summarize_outcome(
                    video_id, monetization_intent, apply_result
                )
                
                # Store outcome in database
                from src.models.video import Video
                video = db.query(Video).filter_by(video_id=video_id).first()
                if video:
                    video.monetization_enabled_intent = True
                    video.monetization_ad_suitability = monetization_intent.ad_suitability
                    video.monetization_ad_formats = ','.join(monetization_intent.ad_formats) if monetization_intent.ad_formats else None
                    video.monetization_paid_promotion = monetization_intent.paid_promotion
                    video.monetization_made_for_kids = monetization_intent.made_for_kids
                    video.monetization_age_restriction = monetization_intent.age_restriction
                    video.monetization_notes = monetization_intent.notes
                    video.monetization_api_applied = monetization_outcome.api_applied
                    video.monetization_completion_state = monetization_outcome.completion_state
                    video.monetization_studio_deeplink = monetization_outcome.studio_deeplink
                    video.monetization_last_attempt_at_utc = datetime.utcnow()
                    db.commit()
                
                # Display outcome table
                outcome_table = monetization_service.format_outcome_table(monetization_intent, monetization_outcome)
                print(outcome_table)
                
                # Log structured event
                logger.info({
                    "event": "monetization_attempt",
                    "video_id": video_id,
                    "intent": {
                        "enable": monetization_intent.enable,
                        "made_for_kids": monetization_intent.made_for_kids,
                        "ad_formats": monetization_intent.ad_formats,
                        "ad_suitability": monetization_intent.ad_suitability,
                        "paid_promotion": monetization_intent.paid_promotion,
                        "age_restriction": monetization_intent.age_restriction
                    },
                    "applied": monetization_outcome.applied_settings,
                    "requires_studio": monetization_outcome.requires_studio,
                    "studio_deeplink": monetization_outcome.studio_deeplink
                })
            
            # Build notification message
            notification_message = f"Metadata optimized via CLI ({'dry-run' if dry_run else 'published'})"
            if publish_at:
                notification_message += f"\n📅 Scheduled to publish: {publish_at['local']}"
                if 'APPLIED' in locals() and schedule_result == 'APPLIED':
                    notification_message += " (YouTube API scheduled)"
                elif 'APPLIED' in locals():
                    notification_message += " (planned time stored, API scheduling not applied)"
            
            if monetization_outcome:
                notification_message += f"\n💰 Monetization: {monetization_outcome.completion_state}"
                if monetization_outcome.studio_deeplink:
                    notification_message += f"\n   Studio: {monetization_outcome.studio_deeplink}"
            
            notifier.notify_success(
                video_id,
                metadata['title'],
                notification_message
            )
            
            # Schedule guardrail check if auto-rollback enabled
            if Config.ENABLE_AUTO_ROLLBACK and not dry_run:
                logger.info(f"Guardrail monitoring scheduled (check in {Config.GUARDRAIL_CHECK_DAYS} days)")
        else:
            logger.error("❌ Failed to update video metadata")
            notifier.notify_failure(video_id, current_title, "Update failed - check logs")
            return False
        
        db.close()
        return True
    
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        return False


def process_batch(batch_file: str, mode: str = 'auto') -> dict:
    """
    Process multiple videos from CSV file.
    
    Args:
        batch_file: Path to CSV file with video URLs
        mode: Processing mode
    
    Returns:
        Dict with processing statistics
    """
    logger.info(f"Processing batch file: {batch_file}")
    
    if not Path(batch_file).exists():
        logger.error(f"Batch file not found: {batch_file}")
        return {'error': 'File not found'}
    
    start_time = time.time()
    results = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'videos': []
    }
    
    try:
        with open(batch_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                video_url = row.get('video_url', row.get('url', ''))
                keywords_str = row.get('keywords', row.get('target_keywords', ''))
                
                if not video_url:
                    continue
                
                results['total'] += 1
                
                # Parse keywords
                keywords = [k.strip() for k in keywords_str.split(',')] if keywords_str else None
                
                # Process video
                success = process_single_video(
                    video_url=video_url,
                    mode=mode,
                    target_keywords=keywords
                )
                
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                results['videos'].append({
                    'url': video_url,
                    'success': success
                })
                
                # Rate limiting
                time.sleep(2)
    
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        results['error'] = str(e)
    
    duration = time.time() - start_time
    results['duration_seconds'] = duration
    
    # Send notification
    notifier = Notifier()
    notifier.notify_batch_complete(
        total=results['total'],
        successful=results['successful'],
        failed=results['failed'],
        duration_seconds=duration
    )
    
    logger.info(f"Batch processing complete: {results['successful']}/{results['total']} successful")
    return results


def check_guardrails(video_id: str) -> bool:
    """
    Manually check guardrails for a video.
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        True if passed, False if rollback needed
    """
    logger.info(f"Checking guardrails for video: {video_id}")
    
    try:
        youtube_client = YouTubeAPIClient()
        analytics = AnalyticsService(youtube_client)
        db = SessionLocal()
        publisher = VideoPublisher(youtube_client, db)
        notifier = Notifier()
        
        # Get video details
        video_details = youtube_client.get_video_details(video_id)
        if not video_details:
            logger.error(f"Video not found: {video_id}")
            return False
        
        current_title = video_details['snippet']['title']
        
        # Get latest version with baseline
        versions = publisher.get_version_history(video_id, limit=5)
        baseline_version = None
        
        for version in versions:
            if version.performance_baseline_json:
                baseline_version = version
                break
        
        if not baseline_version:
            logger.warning("No baseline metrics found for comparison")
            return True
        
        # Check performance
        result = analytics.check_performance_guardrails(
            video_id=video_id,
            baseline=baseline_version.performance_baseline_json,
            check_days=Config.GUARDRAIL_CHECK_DAYS
        )
        
        if result['should_rollback']:
            logger.warning(f"Guardrail failed: {result['reason']}")
            
            if Config.ENABLE_AUTO_ROLLBACK:
                logger.info("Initiating auto-rollback...")
                
                # Find version before the problematic one
                rollback_target = None
                for i, version in enumerate(versions):
                    if version.id == baseline_version.id and i + 1 < len(versions):
                        rollback_target = versions[i + 1]
                        break
                
                if rollback_target:
                    success = publisher.rollback_to_version(
                        video_id=video_id,
                        version_id=rollback_target.id,
                        reason='auto_rollback_guardrail_failed'
                    )
                    
                    if success:
                        logger.info("✅ Successfully rolled back")
                        notifier.notify_rollback(
                            video_id,
                            current_title,
                            result['reason'],
                            result
                        )
                        db.close()
                        return False
                    else:
                        logger.error("❌ Rollback failed")
                else:
                    logger.warning("No previous version found for rollback")
            else:
                logger.info("Auto-rollback disabled - manual intervention required")
        else:
            logger.info(f"✅ Guardrail passed: {result['reason']}")
        
        db.close()
        return not result['should_rollback']
    
    except Exception as e:
        logger.error(f"Error checking guardrails: {e}", exc_info=True)
        return False


def handle_upload(args) -> int:
    """
    Handle video upload commands.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Exit code (0 for success)
    """
    import os
    import glob
    from src.services.uploader import VideoUploader, list_video_categories
    
    # Initialize YouTube client and uploader
    youtube_client = YouTubeAPIClient()
    uploader = VideoUploader(youtube_client)
    
    # Collect files to upload
    files_to_upload = []
    
    if args.upload:
        # Single file upload
        if not os.path.exists(args.upload):
            logger.error(f"File not found: {args.upload}")
            return 1
        files_to_upload.append(args.upload)
    
    elif args.upload_folder:
        # Folder upload
        if not os.path.isdir(args.upload_folder):
            logger.error(f"Folder not found: {args.upload_folder}")
            return 1
        
        # Find video files
        video_extensions = ['*.mp4', '*.mov', '*.avi', '*.mkv', '*.webm', '*.m4v', '*.TS']
        for ext in video_extensions:
            pattern = os.path.join(args.upload_folder, ext)
            files_to_upload.extend(glob.glob(pattern))
            # Also check lowercase
            pattern_lower = os.path.join(args.upload_folder, ext.lower())
            files_to_upload.extend(glob.glob(pattern_lower))
        
        # Remove duplicates and sort
        files_to_upload = sorted(set(files_to_upload))
        
        if not files_to_upload:
            logger.error(f"No video files found in: {args.upload_folder}")
            return 1
    
    logger.info(f"Found {len(files_to_upload)} video(s) to upload")
    
    # Upload results tracking
    uploaded = []
    failed = []
    
    # Process each file
    for i, file_path in enumerate(files_to_upload, 1):
        file_name = os.path.basename(file_path)
        file_size_mb = os.path.getsize(file_path) / 1024 / 1024
        
        print(f"\n{'='*80}")
        print(f"UPLOADING [{i}/{len(files_to_upload)}]: {file_name}")
        print(f"Size: {file_size_mb:.1f} MB")
        print(f"{'='*80}")
        
        # Determine title
        title = args.title if args.title and len(files_to_upload) == 1 else None
        if not title:
            # Use filename as title
            title = os.path.splitext(file_name)[0]
            title = title.replace('_', ' ').replace('-', ' ')
            title = ' '.join(title.split())  # Normalize spaces
        
        # Upload
        try:
            result = uploader.upload_video(
                file_path=file_path,
                title=title[:100],  # Max 100 chars
                description=args.description or f"Video uploaded via YouTube SEO tool",
                tags=[],
                category=args.category,
                privacy_status=args.privacy,
                notify_subscribers=False  # Don't notify until SEO is done
            )
            
            if result:
                video_id = result.get('id')
                logger.info(f"✅ Upload successful: {video_id}")
                logger.info(f"   URL: https://www.youtube.com/watch?v={video_id}")
                uploaded.append({
                    'file': file_name,
                    'video_id': video_id,
                    'title': title
                })
                
                # Process with SEO if requested
                if args.process_after_upload:
                    logger.info("Processing with SEO generator...")
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    # Wait a bit for YouTube to process
                    logger.info("Waiting 30s for YouTube to process video...")
                    time.sleep(30)
                    
                    success = process_single_video(
                        video_url=video_url,
                        mode='auto',
                        dry_run=args.dry_run
                    )
                    if success:
                        logger.info("✅ SEO metadata updated")
                    else:
                        logger.warning("⚠️  SEO processing failed (video uploaded but not optimized)")
            else:
                logger.error(f"❌ Upload failed: {file_name}")
                failed.append({'file': file_name, 'error': 'Upload returned None'})
        
        except Exception as e:
            logger.error(f"❌ Error uploading {file_name}: {e}")
            failed.append({'file': file_name, 'error': str(e)})
        
        # Sleep between uploads (except for last one)
        if i < len(files_to_upload):
            sleep_time = args.upload_sleep
            logger.info(f"Sleeping {sleep_time}s before next upload...")
            time.sleep(sleep_time)
    
    # Summary
    print(f"\n{'='*80}")
    print("UPLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"Total files: {len(files_to_upload)}")
    print(f"Successful: {len(uploaded)}")
    print(f"Failed: {len(failed)}")
    
    if uploaded:
        print(f"\n✅ Uploaded videos:")
        for item in uploaded:
            print(f"   - {item['file']} -> {item['video_id']}")
    
    if failed:
        print(f"\n❌ Failed uploads:")
        for item in failed:
            print(f"   - {item['file']}: {item['error']}")
    
    print(f"{'='*80}\n")
    
    # Save uploaded video IDs for later processing
    if uploaded:
        ids_file = f"logs/uploaded_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        os.makedirs('logs', exist_ok=True)
        with open(ids_file, 'w') as f:
            for item in uploaded:
                f.write(f"{item['video_id']}\n")
        logger.info(f"Video IDs saved to: {ids_file}")
    
    return 0 if not failed else 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='YouTube SEO Metadata Generator & Auto-Updater',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single video (auto-publish)
  python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode auto

  # Preview without publishing
  python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --mode preview

  # Process with custom keywords
  python main.py --url "..." --keywords "python,tutorial,beginners"
  
  # Schedule video publication with ISO 8601 format
  python main.py --url "..." --mode auto --publish-at "2025-11-10T14:00:00+01:00"
  
  # Schedule with IANA timezone
  python main.py --url "..." --mode auto --publish-at "2025-11-10 14:00 Europe/Amsterdam"
  
  # Schedule with separate timezone flag
  python main.py --url "..." --mode auto --publish-at "2025-11-10 14:00" --tz "Europe/Amsterdam"

  # Batch process from CSV
  python main.py --batch videos.csv --mode auto

  # Check guardrails
  python main.py --check-guardrails VIDEO_ID

  # Upload a single video
  python main.py --upload /path/to/video.mp4 --title "My Video Title"

  # Upload all videos in a folder
  python main.py --upload-folder /path/to/videos --privacy private

  # Initialize database
  python main.py --init-db
        """
    )
    
    parser.add_argument('--url', help='YouTube video URL')
    parser.add_argument('--mode', choices=['auto', 'preview'], default='auto',
                       help='Processing mode: auto (publish) or preview (show only)')
    parser.add_argument('--keywords', help='Target keywords (comma-separated)')
    parser.add_argument('--batch', help='CSV file with video URLs for batch processing')
    parser.add_argument('--check-guardrails', metavar='VIDEO_ID',
                       help='Check performance guardrails for a video')
    parser.add_argument('--check-monetization', metavar='VIDEO_ID',
                       help='Check monetization eligibility status for a video')
    
    # Upload options
    parser.add_argument('--upload', metavar='FILE',
                       help='Upload a video file to YouTube')
    parser.add_argument('--upload-folder', metavar='FOLDER',
                       help='Upload all video files in a folder')
    parser.add_argument('--title', help='Video title for upload (default: filename)')
    parser.add_argument('--description', help='Video description for upload')
    parser.add_argument('--privacy', choices=['public', 'private', 'unlisted'], default='private',
                       help='Privacy status for uploaded videos (default: private)')
    parser.add_argument('--category', default='education',
                       help='Video category (e.g., education, howto, entertainment)')
    parser.add_argument('--process-after-upload', action='store_true',
                       help='Process uploaded videos with SEO generator')
    parser.add_argument('--upload-sleep', type=int, default=5,
                       help='Seconds to sleep between uploads (default: 5)')
    
    # Monetization options
    parser.add_argument('--enable-monetization', action='store_true',
                       help='Enable monetization when processing video (use with --url)')
    parser.add_argument('--made-for-kids', type=str, choices=['true', 'false'],
                       help='Set made-for-kids status (true|false)')
    parser.add_argument('--paid-promotion', type=str, choices=['none', 'includes', 'not_sure'],
                       help='Paid promotion disclosure (none|includes|not_sure)')
    parser.add_argument('--ad-suitability', type=str, choices=['standard', 'limited', 'mature', 'not_sure'],
                       help='Ad suitability self-certification (standard|limited|mature|not_sure)')
    parser.add_argument('--ad-formats', type=str,
                       help='Desired ad formats, comma-separated (e.g., "skippable,overlay,display")')
    parser.add_argument('--age-restriction', type=str, choices=['none', '18+'],
                       help='Age restriction setting (none|18+)')
    parser.add_argument('--monetization-notes', type=str,
                       help='Free-text notes about monetization intent')
    parser.add_argument('--assume-ypp-eligible', action='store_true',
                       help='Skip YPP eligibility checks')
    parser.add_argument('--no-deeplink', action='store_true',
                       help='Suppress Studio deeplink generation')
    parser.add_argument('--fail-on-incomplete', action='store_true',
                       help='Exit non-zero if monetization requires Studio completion')
    
    # Other options
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (don\'t actually update YouTube)')
    parser.add_argument('--publish-at', metavar='DATETIME',
                       help='Schedule publication datetime (e.g., "2025-11-10T14:00:00+01:00" or "2025-11-10 14:00 Europe/Amsterdam")')
    parser.add_argument('--tz', metavar='TIMEZONE',
                       help='IANA timezone for --publish-at if not specified in datetime (e.g., "Europe/Amsterdam")')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database')
    parser.add_argument('--version', action='version', version='YouTube SEO Tool v1.0.0')
    
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        return 0
    
    # Validate configuration
    if not validate_config():
        return 1
    
    # Display configuration
    logger.info(f"Using LLM provider: {Config.get_llm_provider()}")
    logger.info(f"Dry run mode: {Config.DRY_RUN_MODE or args.dry_run}")
    
    # Handle upload commands
    if args.upload or args.upload_folder:
        return handle_upload(args)
    
    # Check monetization status
    if args.check_monetization:
        video_id = args.check_monetization
        if not validate_video_id_format(video_id):
            logger.error(f"Invalid video ID format: {video_id}")
            return 1
        
        logger.info(f"Checking monetization status for video: {video_id}")
        youtube_api = YouTubeAPIClient()
        status = youtube_api.check_monetization_status(video_id)
        
        if 'error' in status:
            logger.error(f"Error: {status['error']}")
            return 1
        
        print(f"\n{'='*80}")
        print("MONETIZATION STATUS")
        print(f"{'='*80}")
        print(f"Video ID: {status['video_id']}")
        print(f"Eligible for monetization: {'✅ Yes' if status['eligible_for_monetization'] else '❌ No'}")
        print(f"Made for kids: {'Yes' if status['made_for_kids'] else 'No'}")
        print(f"License: {status['license']}")
        print(f"Privacy: {status['privacy']}")
        print(f"\nNote: {status['note']}")
        print(f"{'='*80}\n")
        
        return 0
    
    # Check guardrails
    if args.check_guardrails:
        video_id = args.check_guardrails
        if not validate_video_id_format(video_id):
            logger.error(f"Invalid video ID format: {video_id}")
            return 1
        
        passed = check_guardrails(video_id)
        return 0 if passed else 1
    
    # Batch processing
    if args.batch:
        results = process_batch(args.batch, mode=args.mode)
        
        if 'error' in results:
            return 1
        
        print(f"\n{'='*80}")
        print("BATCH PROCESSING RESULTS")
        print(f"{'='*80}")
        print(f"Total: {results['total']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Duration: {results['duration_seconds']:.1f}s")
        print(f"{'='*80}\n")
        
        return 0 if results['failed'] == 0 else 1
    
    # Single video processing
    if args.url:
        keywords = None
        if args.keywords:
            keywords = [k.strip() for k in args.keywords.split(',')]
        
        # Parse publish_at if provided
        publish_at_context = None
        if args.publish_at:
            try:
                from src.utils.validators import parse_publish_at
                parsed = parse_publish_at(args.publish_at, args.tz)
                publish_at_context = {
                    'utc': parsed.utc_rfc3339,
                    'tz': parsed.tz,
                    'local': parsed.local_display,
                    'utc_dt': parsed.utc,
                    'local_dt': parsed.local
                }
                logger.info(f"📅 Scheduled for: {parsed.local_display}")
            except ValueError as e:
                logger.error(str(e))
                return 2  # Exit code 2 for validation errors
        
        # Prepare monetization intent if requested
        monetization_intent = None
        if args.enable_monetization:
            monetization_service = MonetizationService(None)  # Temp instance for preparing intent
            monetization_intent = monetization_service.prepare_intent_from_cli(args)
            
            # Convert string 'true'/'false' to boolean for made_for_kids
            if hasattr(args, 'made_for_kids') and args.made_for_kids:
                monetization_intent.made_for_kids = args.made_for_kids == 'true'
        
        success = process_single_video(
            video_url=args.url,
            mode=args.mode,
            target_keywords=keywords,
            dry_run=args.dry_run,
            enable_monetization=args.enable_monetization,
            publish_at=publish_at_context,
            monetization_intent=monetization_intent
        )
        
        # Check fail-on-incomplete
        if monetization_intent and monetization_intent.fail_on_incomplete:
            # This would require access to the outcome, which we'd need to return from process_single_video
            # For now, we'll handle this in a future enhancement
            pass
        
        return 0 if success else 1
    
    # No action specified
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
