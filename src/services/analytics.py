"""Analytics service for performance monitoring and guardrail checks."""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger('analytics')


class AnalyticsService:
    """Service for YouTube Analytics and performance monitoring."""
    
    def __init__(self, youtube_client):
        """
        Initialize analytics service.
        
        Args:
            youtube_client: YouTubeAPIClient instance with analytics access
        """
        self.youtube_client = youtube_client
        self.analytics = youtube_client.analytics
    
    def get_baseline_metrics(
        self,
        video_id: str,
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Get baseline performance metrics for a video.
        
        Args:
            video_id: YouTube video ID
            days: Number of days to look back
        
        Returns:
            Dict with metrics or None if error
        """
        logger.info(f"Fetching baseline metrics for {video_id} ({days} days)")
        
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views,estimatedMinutesWatched,averageViewDuration,likes,dislikes,comments,shares,subscribersGained,subscribersLost,impressions,impressionClickThroughRate',
                filters=f'video=={video_id}',
                dimensions='day'
            ).execute()
            
            if not response.get('rows'):
                logger.warning(f"No analytics data found for {video_id}")
                return None
            
            # Aggregate metrics
            total_views = 0
            total_watch_time = 0
            total_impressions = 0
            ctr_values = []
            avg_view_duration_values = []
            
            for row in response['rows']:
                day_metrics = dict(zip(response['columnHeaders'], row))
                total_views += day_metrics.get('views', 0)
                total_watch_time += day_metrics.get('estimatedMinutesWatched', 0)
                total_impressions += day_metrics.get('impressions', 0)
                
                if day_metrics.get('impressionClickThroughRate'):
                    ctr_values.append(day_metrics['impressionClickThroughRate'])
                if day_metrics.get('averageViewDuration'):
                    avg_view_duration_values.append(day_metrics['averageViewDuration'])
            
            # Calculate averages
            avg_ctr = sum(ctr_values) / len(ctr_values) if ctr_values else 0
            avg_view_duration = sum(avg_view_duration_values) / len(avg_view_duration_values) if avg_view_duration_values else 0
            
            baseline = {
                'video_id': video_id,
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_views': total_views,
                'total_watch_time_minutes': total_watch_time,
                'total_impressions': total_impressions,
                'average_ctr': avg_ctr,
                'average_view_duration_seconds': avg_view_duration,
                'collected_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Baseline metrics: CTR={avg_ctr:.2%}, Views={total_views}, Impressions={total_impressions}")
            return baseline
        
        except Exception as e:
            logger.error(f"Error fetching baseline metrics: {e}")
            return None
    
    def check_performance_guardrails(
        self,
        video_id: str,
        baseline: Dict[str, Any],
        check_days: int = 3
    ) -> Dict[str, Any]:
        """
        Check if video performance has degraded after metadata change.
        
        Args:
            video_id: YouTube video ID
            baseline: Baseline metrics dict
            check_days: Number of recent days to check
        
        Returns:
            Dict with 'passed', 'ctr_drop', 'impressions_change', 'should_rollback'
        """
        logger.info(f"Checking performance guardrails for {video_id}")
        
        try:
            # Get recent metrics
            recent_metrics = self.get_baseline_metrics(video_id, days=check_days)
            
            if not recent_metrics:
                logger.warning("No recent metrics available for guardrail check")
                return {
                    'passed': None,
                    'reason': 'No recent data available',
                    'should_rollback': False
                }
            
            # Extract values
            baseline_ctr = baseline.get('average_ctr', 0)
            recent_ctr = recent_metrics.get('average_ctr', 0)
            
            baseline_impressions = baseline.get('total_impressions', 0)
            recent_impressions = recent_metrics.get('total_impressions', 0)
            
            # Calculate changes
            ctr_drop_percent = 0
            if baseline_ctr > 0:
                ctr_drop_percent = ((baseline_ctr - recent_ctr) / baseline_ctr) * 100
            
            impressions_change_percent = 0
            if baseline_impressions > 0:
                impressions_change_percent = ((recent_impressions - baseline_impressions) / baseline_impressions) * 100
            
            # Check thresholds
            ctr_threshold = Config.GUARDRAIL_CTR_DROP_THRESHOLD
            impressions_variance = Config.GUARDRAIL_IMPRESSIONS_VARIANCE
            
            # Determine if rollback needed
            should_rollback = False
            reason = []
            
            if ctr_drop_percent > ctr_threshold:
                reason.append(f"CTR dropped {ctr_drop_percent:.1f}% (threshold: {ctr_threshold}%)")
                
                # Only rollback if impressions are stable (not just low traffic)
                if abs(impressions_change_percent) <= impressions_variance:
                    should_rollback = True
                else:
                    reason.append(f"But impressions changed {impressions_change_percent:.1f}% (unstable traffic)")
            
            passed = not should_rollback
            
            result = {
                'passed': passed,
                'should_rollback': should_rollback,
                'ctr_drop_percent': ctr_drop_percent,
                'impressions_change_percent': impressions_change_percent,
                'baseline_ctr': baseline_ctr,
                'recent_ctr': recent_ctr,
                'baseline_impressions': baseline_impressions,
                'recent_impressions': recent_impressions,
                'reason': '; '.join(reason) if reason else 'Performance within acceptable range',
                'checked_at': datetime.utcnow().isoformat()
            }
            
            if should_rollback:
                logger.warning(f"Guardrail failed: {result['reason']}")
            else:
                logger.info(f"Guardrail passed: {result['reason']}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error checking guardrails: {e}")
            return {
                'passed': None,
                'reason': f'Error: {str(e)}',
                'should_rollback': False
            }
    
    def get_traffic_sources(self, video_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get traffic source breakdown for a video.
        
        Args:
            video_id: YouTube video ID
            days: Number of days to analyze
        
        Returns:
            Dict with traffic source data
        """
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='views',
                filters=f'video=={video_id}',
                dimensions='insightTrafficSourceType'
            ).execute()
            
            if not response.get('rows'):
                return None
            
            traffic_sources = {}
            total_views = 0
            
            for row in response['rows']:
                source_type = row[0]
                views = row[1]
                traffic_sources[source_type] = views
                total_views += views
            
            # Calculate percentages
            for source in traffic_sources:
                percentage = (traffic_sources[source] / total_views * 100) if total_views > 0 else 0
                traffic_sources[source] = {
                    'views': traffic_sources[source],
                    'percentage': percentage
                }
            
            logger.info(f"Traffic sources for {video_id}: {list(traffic_sources.keys())}")
            return {
                'video_id': video_id,
                'total_views': total_views,
                'sources': traffic_sources,
                'period_days': days
            }
        
        except Exception as e:
            logger.error(f"Error getting traffic sources: {e}")
            return None
    
    def generate_performance_report(
        self,
        video_id: str,
        before_date: str,
        after_date: str
    ) -> Dict[str, Any]:
        """
        Generate a before/after performance report.
        
        Args:
            video_id: YouTube video ID
            before_date: ISO date string for "before" period end
            after_date: ISO date string for "after" period end
        
        Returns:
            Performance comparison dict
        """
        logger.info(f"Generating performance report for {video_id}")
        
        try:
            before_dt = datetime.fromisoformat(before_date)
            after_dt = datetime.fromisoformat(after_date)
            
            # Get before metrics (7 days before the date)
            before_start = (before_dt - timedelta(days=7)).date()
            before_end = before_dt.date()
            
            before_response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=before_start.isoformat(),
                endDate=before_end.isoformat(),
                metrics='views,impressions,impressionClickThroughRate,averageViewDuration',
                filters=f'video=={video_id}'
            ).execute()
            
            # Get after metrics (7 days after the date)
            after_start = after_dt.date()
            after_end = (after_dt + timedelta(days=7)).date()
            
            after_response = self.analytics.reports().query(
                ids='channel==MINE',
                startDate=after_start.isoformat(),
                endDate=after_end.isoformat(),
                metrics='views,impressions,impressionClickThroughRate,averageViewDuration',
                filters=f'video=={video_id}'
            ).execute()
            
            # Parse results
            def parse_metrics(response):
                if not response.get('rows'):
                    return None
                row = response['rows'][0]
                headers = [h['name'] for h in response['columnHeaders']]
                return dict(zip(headers, row))
            
            before_metrics = parse_metrics(before_response)
            after_metrics = parse_metrics(after_response)
            
            if not before_metrics or not after_metrics:
                return {'error': 'Insufficient data for comparison'}
            
            # Calculate changes
            def calc_change(before, after):
                if before == 0:
                    return 0
                return ((after - before) / before) * 100
            
            report = {
                'video_id': video_id,
                'before': before_metrics,
                'after': after_metrics,
                'changes': {
                    'views': calc_change(before_metrics.get('views', 0), after_metrics.get('views', 0)),
                    'impressions': calc_change(before_metrics.get('impressions', 0), after_metrics.get('impressions', 0)),
                    'ctr': calc_change(before_metrics.get('impressionClickThroughRate', 0), after_metrics.get('impressionClickThroughRate', 0)),
                    'avg_view_duration': calc_change(before_metrics.get('averageViewDuration', 0), after_metrics.get('averageViewDuration', 0))
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
