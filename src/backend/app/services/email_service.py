"""Email service for sending transactional emails.

Provides an abstract interface with implementations for:
- Azure Communication Services (production)
- Mock service (development/testing)
"""

import logging
from abc import ABC, abstractmethod

from azure.communication.email import EmailClient

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailServiceInterface(ABC):
    """Abstract interface for email services."""

    @abstractmethod
    async def send_password_reset(
        self, to_email: str, reset_link: str, display_name: str | None
    ) -> bool:
        """Send password reset email.

        Args:
            to_email: Recipient email address
            reset_link: URL with reset token
            display_name: User's display name (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_approval_notification(
        self, to_email: str, display_name: str | None, approved: bool
    ) -> bool:
        """Send account approval/rejection notification.

        Args:
            to_email: Recipient email address
            display_name: User's display name (optional)
            approved: True if approved, False if rejected

        Returns:
            True if sent successfully, False otherwise
        """
        pass


class AzureCommunicationEmailService(EmailServiceInterface):
    """Azure Communication Services email implementation."""

    def __init__(self, connection_string: str, sender: str):
        """Initialize with Azure connection string and sender address."""
        self.connection_string = connection_string
        self.sender = sender

    async def send_password_reset(
        self, to_email: str, reset_link: str, display_name: str | None
    ) -> bool:
        """Send password reset email via Azure Communication Services."""
        name = display_name or "there"
        message = {
            "senderAddress": self.sender,
            "recipients": {"to": [{"address": to_email}]},
            "content": {
                "subject": "EnglishConnect - Reset Your Password",
                "plainText": (
                    f"Hi {name},\n\n"
                    f"Click here to reset your password: {reset_link}\n\n"
                    "This link expires in 1 hour.\n\n"
                    "If you didn't request this, please ignore this email."
                ),
                "html": (
                    f"<p>Hi {name},</p>"
                    f'<p>Click <a href="{reset_link}">here</a> to reset your password.</p>'
                    "<p>This link expires in 1 hour.</p>"
                    "<p>If you didn't request this, please ignore this email.</p>"
                ),
            },
        }

        try:
            client = EmailClient.from_connection_string(self.connection_string)
            poller = client.begin_send(message)
            poller.result()
            logger.info(f"Password reset email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False

    async def send_approval_notification(
        self, to_email: str, display_name: str | None, approved: bool
    ) -> bool:
        """Send account approval/rejection notification via Azure."""
        name = display_name or "there"

        if approved:
            subject = "EnglishConnect - Your Account is Approved!"
            text = (
                f"Hi {name},\n\n"
                "Great news! Your EnglishConnect account has been approved.\n\n"
                "You can now log in and start practicing English.\n\n"
                "Welcome to EnglishConnect!"
            )
            html = (
                f"<p>Hi {name},</p>"
                "<p><strong>Great news!</strong> Your EnglishConnect account has been approved.</p>"
                "<p>You can now log in and start practicing English.</p>"
                "<p>Welcome to EnglishConnect!</p>"
            )
        else:
            subject = "EnglishConnect - Account Status Update"
            text = (
                f"Hi {name},\n\n"
                "We're sorry, but your EnglishConnect account request was not approved.\n\n"
                "If you believe this was a mistake, please contact your instructor."
            )
            html = (
                f"<p>Hi {name},</p>"
                "<p>We're sorry, but your EnglishConnect account request was not approved.</p>"
                "<p>If you believe this was a mistake, please contact your instructor.</p>"
            )

        message = {
            "senderAddress": self.sender,
            "recipients": {"to": [{"address": to_email}]},
            "content": {
                "subject": subject,
                "plainText": text,
                "html": html,
            },
        }

        try:
            client = EmailClient.from_connection_string(self.connection_string)
            poller = client.begin_send(message)
            poller.result()
            status = "approved" if approved else "rejected"
            logger.info(f"Approval notification ({status}) sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send approval notification to {to_email}: {e}")
            return False


class MockEmailService(EmailServiceInterface):
    """Mock email service for development and testing."""

    async def send_password_reset(
        self, to_email: str, reset_link: str, display_name: str | None
    ) -> bool:
        """Log password reset email instead of sending."""
        logger.info(
            f"[MOCK EMAIL] Password reset for {to_email}: {reset_link}"
        )
        return True

    async def send_approval_notification(
        self, to_email: str, display_name: str | None, approved: bool
    ) -> bool:
        """Log approval notification instead of sending."""
        status = "approved" if approved else "rejected"
        logger.info(
            f"[MOCK EMAIL] Account {status} notification for {to_email}"
        )
        return True


def get_email_service() -> EmailServiceInterface:
    """Factory function to get the configured email service.

    Returns:
        AzureCommunicationEmailService if Azure connection string is configured,
        MockEmailService otherwise.
    """
    settings = get_settings()

    if settings.azure_communication_connection_string:
        return AzureCommunicationEmailService(
            connection_string=settings.azure_communication_connection_string,
            sender=settings.email_sender_address,
        )

    return MockEmailService()
