"""Notification service for Slack and Email alerts."""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, Any
import requests

from ..utils.logger import get_logger
from ..utils.config import Config

logger = get_logger('notifier')


class Notifier:
    """Service for sending notifications via Slack and Email."""
    
    def __init__(self):
        """Initialize notifier with configured channels."""
        self.slack_enabled = bool(Config.SLACK_WEBHOOK_URL)
        self.email_enabled = bool(Config.EMAIL_FROM and Config.EMAIL_TO)
        
        if not self.slack_enabled and not self.email_enabled:
            logger.warning("No notification channels configured")
    
    def notify_success(
        self,
        video_id: str,
        title: str,
        message: str = "Metadata updated successfully"
    ):
        """
        Send success notification.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            message: Success message
        """
        subject = f"✅ YouTube SEO Update Success: {title[:50]}"
        body = f"""
<b>Video:</b> {title}
<b>Video ID:</b> {video_id}
<b>Status:</b> Success
<b>Message:</b> {message}

<a href="https://www.youtube.com/watch?v={video_id}">View Video</a> | <a href="https://studio.youtube.com/video/{video_id}/edit">Edit in Studio</a>
"""
        
        self._send_notification(subject, body, color='good')
    
    def notify_failure(
        self,
        video_id: str,
        title: str,
        error: str
    ):
        """
        Send failure notification.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            error: Error message
        """
        subject = f"❌ YouTube SEO Update Failed: {title[:50]}"
        body = f"""
<b>Video:</b> {title}
<b>Video ID:</b> {video_id}
<b>Status:</b> Failed
<b>Error:</b> {error}

Please check the logs for more details.
"""
        
        self._send_notification(subject, body, color='danger')
    
    def notify_rollback(
        self,
        video_id: str,
        title: str,
        reason: str,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Send rollback notification.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            reason: Reason for rollback
            metrics: Performance metrics that triggered rollback
        """
        subject = f"↩️ Auto-Rollback Triggered: {title[:50]}"
        
        metrics_text = ""
        if metrics:
            metrics_text = f"""
<b>Performance Metrics:</b>
- CTR Drop: {metrics.get('ctr_drop_percent', 0):.1f}%
- Baseline CTR: {metrics.get('baseline_ctr', 0):.2%}
- Recent CTR: {metrics.get('recent_ctr', 0):.2%}
- Impressions Change: {metrics.get('impressions_change_percent', 0):.1f}%
"""
        
        body = f"""
<b>Video:</b> {title}
<b>Video ID:</b> {video_id}
<b>Status:</b> Rolled Back
<b>Reason:</b> {reason}
{metrics_text}
<a href="https://studio.youtube.com/video/{video_id}/analytics">View Analytics</a>
"""
        
        self._send_notification(subject, body, color='warning')
    
    def notify_batch_complete(
        self,
        total: int,
        successful: int,
        failed: int,
        duration_seconds: float
    ):
        """
        Send batch processing completion notification.
        
        Args:
            total: Total videos processed
            successful: Number of successful updates
            failed: Number of failed updates
            duration_seconds: Processing duration
        """
        subject = f"📦 Batch Processing Complete: {successful}/{total} successful"
        body = f"""
<b>Batch Processing Summary</b>

<b>Total Videos:</b> {total}
<b>Successful:</b> {successful}
<b>Failed:</b> {failed}
<b>Duration:</b> {duration_seconds:.1f} seconds

<b>Success Rate:</b> {(successful/total*100):.1f}%
"""
        
        color = 'good' if failed == 0 else 'warning'
        self._send_notification(subject, body, color=color)
    
    def notify_scheduled_optimization(
        self,
        video_id: str,
        title: str,
        changes_made: bool,
        reason: str
    ):
        """
        Send scheduled re-optimization notification.
        
        Args:
            video_id: YouTube video ID
            title: Video title
            changes_made: Whether changes were made
            reason: Reason for optimization
        """
        status = "✨ Re-optimized" if changes_made else "ℹ️ No Changes"
        subject = f"{status}: {title[:50]}"
        body = f"""
<b>Video:</b> {title}
<b>Video ID:</b> {video_id}
<b>Status:</b> {'Metadata updated' if changes_made else 'No changes needed'}
<b>Reason:</b> {reason}

<a href="https://www.youtube.com/watch?v={video_id}">View Video</a>
"""
        
        color = 'good' if changes_made else None
        self._send_notification(subject, body, color=color)
    
    def _send_notification(
        self,
        subject: str,
        body: str,
        color: Optional[str] = None
    ):
        """
        Send notification via all enabled channels.
        
        Args:
            subject: Notification subject
            body: Notification body (supports HTML)
            color: Slack attachment color ('good', 'warning', 'danger')
        """
        if self.slack_enabled:
            self._send_slack(subject, body, color)
        
        if self.email_enabled:
            self._send_email(subject, body)
    
    def _send_slack(
        self,
        subject: str,
        body: str,
        color: Optional[str] = None
    ):
        """
        Send notification to Slack.
        
        Args:
            subject: Message title
            body: Message body
            color: Attachment color
        """
        try:
            # Convert HTML to Slack markdown
            slack_body = body.replace('<b>', '*').replace('</b>', '*')
            slack_body = slack_body.replace('<a href="', '<').replace('">', '|').replace('</a>', '>')
            
            payload = {
                'text': subject,
                'attachments': [{
                    'text': slack_body,
                    'color': color,
                    'mrkdwn_in': ['text']
                }]
            }
            
            response = requests.post(
                Config.SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def _send_email(self, subject: str, body: str):
        """
        Send notification via email.
        
        Args:
            subject: Email subject
            body: Email body (HTML)
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = Config.EMAIL_FROM
            msg['To'] = Config.EMAIL_TO
            
            # Create HTML version
            html_body = f"""
<html>
<head></head>
<body>
{body}
<hr>
<p><small>YouTube SEO Auto-Updater</small></p>
</body>
</html>
"""
            
            # Attach HTML
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send via SMTP
            with smtplib.SMTP(Config.EMAIL_SMTP_HOST, Config.EMAIL_SMTP_PORT) as server:
                server.starttls()
                if Config.EMAIL_PASSWORD:
                    server.login(Config.EMAIL_FROM, Config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            logger.info("Email notification sent successfully")
        
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
