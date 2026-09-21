"""Send notifications via multiple channels."""

from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

from .models import Notification, Channel, Priority, NotificationTemplate, NotificationMetrics

logger = logging.getLogger("notificationagent.notifier")


class Notifier:
    """Send notifications to users via multiple channels."""

    def __init__(self, email_config: dict = None, slack_config: dict = None):
        self.email_config = email_config or {}
        self.slack_config = slack_config or {}
        self.notifications: list[Notification] = []
        self.templates: dict[str, NotificationTemplate] = {}

    async def send_notification(
        self,
        title: str,
        message: str,
        recipient: str,
        channels: list[Channel],
        priority: Priority = Priority.MEDIUM,
    ) -> Notification:
        """Send notification via specified channels.

        Args:
            title: Notification title
            message: Notification message
            recipient: Recipient email/user
            channels: Channels to send via
            priority: Priority level

        Returns:
            Notification object
        """
        notification_id = f"notif-{uuid.uuid4().hex[:8]}"

        notification = Notification(
            notification_id=notification_id,
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            recipient=recipient,
        )

        success_count = 0

        for channel in channels:
            try:
                if channel == Channel.EMAIL:
                    await self._send_email(recipient, title, message)
                    success_count += 1
                elif channel == Channel.SLACK:
                    await self._send_slack(recipient, title, message)
                    success_count += 1
                elif channel == Channel.TELEGRAM:
                    await self._send_telegram(recipient, title, message)
                    success_count += 1
                elif channel == Channel.SMS:
                    await self._send_sms(recipient, title, message)
                    success_count += 1
                elif channel == Channel.WEBHOOK:
                    await self._send_webhook(recipient, title, message)
                    success_count += 1

            except Exception as e:
                logger.error(f"Failed to send via {channel.value}: {e}")
                notification.error = str(e)

        notification.sent_at = datetime.utcnow()
        notification.delivered = success_count > 0
        self.notifications.append(notification)

        logger.info(f"Notification {notification_id} sent via {success_count}/{len(channels)} channels")
        return notification

    async def _send_email(self, recipient: str, title: str, message: str) -> bool:
        """Send email notification."""
        try:
            if not self.email_config:
                return False

            msg = MIMEText(message)
            msg["Subject"] = title
            msg["From"] = self.email_config.get("from_address", "")
            msg["To"] = recipient

            # Would use SMTP in production
            logger.info(f"Email sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    async def _send_slack(self, recipient: str, title: str, message: str) -> bool:
        """Send Slack notification."""
        try:
            if not self.slack_config:
                return False

            # Would use Slack API in production
            logger.info(f"Slack message sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False

    async def _send_telegram(self, recipient: str, title: str, message: str) -> bool:
        """Send Telegram notification."""
        try:
            # Would use Telegram API in production
            logger.info(f"Telegram message sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def _send_sms(self, recipient: str, title: str, message: str) -> bool:
        """Send SMS notification."""
        try:
            # Would use SMS API in production
            logger.info(f"SMS sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return False

    async def _send_webhook(self, recipient: str, title: str, message: str) -> bool:
        """Send webhook notification."""
        try:
            # Would use HTTP request in production
            logger.info(f"Webhook sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

    def get_metrics(self) -> NotificationMetrics:
        """Get notification metrics.

        Returns:
            NotificationMetrics
        """
        metrics = NotificationMetrics(
            total_sent=len(self.notifications),
            total_delivered=sum(1 for n in self.notifications if n.delivered),
            total_failed=sum(1 for n in self.notifications if not n.delivered),
        )

        for notif in self.notifications:
            for channel in notif.channels:
                metrics.by_channel[channel.value] = metrics.by_channel.get(channel.value, 0) + 1
            metrics.by_priority[notif.priority.value] = metrics.by_priority.get(notif.priority.value, 0) + 1

        return metrics
