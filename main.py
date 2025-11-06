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
    publish_at: dict = None
) -> bool:
    """
    Process a single video.
    
    Args:
        video_url: YouTube video URL
        mode: 'auto' (publish immediately) or 'preview' (show only)
        target_keywords: Optional list of target keywords
        dry_run: If True, don't actually update YouTube
        enable_monetization: If True, enable monetization for the video
        publish_at: Optional dict with UTC datetime, timezone, and local display
    
    Returns:
        True if successful
    """
    logger.info(f"Processing video: {video_url}")
    
    # Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {video_url}")
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
        
        logger.info(f"Processing: {current_title}")
        
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
        
        # Prepare context with publish_at if available
        generation_context = {}
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
            
            # Enable monetization if requested
            if enable_monetization and not dry_run:
                logger.info("Enabling monetization for video...")
                monetization_success = youtube_client.enable_monetization(video_id)
                if monetization_success:
                    logger.info("✅ Monetization settings updated")
                    logger.warning("⚠️  Complete monetization setup in YouTube Studio:")
                    logger.warning("   1. Go to https://studio.youtube.com")
                    logger.warning("   2. Select the video")
                    logger.warning("   3. Go to Monetization tab")
                    logger.warning("   4. Enable monetization and select ad types")
                else:
                    logger.error("❌ Failed to enable monetization")
            
            # Build notification message
            notification_message = f"Metadata optimized via CLI ({'dry-run' if dry_run else 'published'})"
            if publish_at:
                notification_message += f"\n📅 Scheduled to publish: {publish_at['local']}"
                if 'APPLIED' in locals() and schedule_result == 'APPLIED':
                    notification_message += " (YouTube API scheduled)"
                elif 'APPLIED' in locals():
                    notification_message += " (planned time stored, API scheduling not applied)"
            
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
    parser.add_argument('--enable-monetization', action='store_true',
                       help='Enable monetization when processing video (use with --url)')
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
        
        success = process_single_video(
            video_url=args.url,
            mode=args.mode,
            target_keywords=keywords,
            dry_run=args.dry_run,
            enable_monetization=args.enable_monetization,
            publish_at=publish_at_context
        )
        
        return 0 if success else 1
    
    # No action specified
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
