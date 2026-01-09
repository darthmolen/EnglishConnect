# tests/unit/test_email_service.py
"""Unit tests for EmailService - TDD: tests written BEFORE implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging


class TestEmailServiceFactory:
    """Tests for email service factory function."""

    def test_get_email_service_returns_mock_when_no_connection_string(self):
        """Should return MockEmailService when no Azure connection string configured."""
        from app.services.email_service import get_email_service, MockEmailService

        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.azure_communication_connection_string = ""
            mock_settings.return_value.email_sender_address = "test@test.com"

            service = get_email_service()

            assert isinstance(service, MockEmailService)

    def test_get_email_service_returns_azure_when_configured(self):
        """Should return AzureCommunicationEmailService when connection string is set."""
        from app.services.email_service import (
            get_email_service,
            AzureCommunicationEmailService,
        )

        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value.azure_communication_connection_string = (
                "endpoint=https://test.communication.azure.com/;accesskey=test123"
            )
            mock_settings.return_value.email_sender_address = "noreply@test.com"

            service = get_email_service()

            assert isinstance(service, AzureCommunicationEmailService)


class TestMockEmailService:
    """Tests for MockEmailService (development/testing)."""

    @pytest.mark.asyncio
    async def test_mock_email_service_logs_password_reset(self, caplog):
        """Mock service should log password reset email instead of sending."""
        from app.services.email_service import MockEmailService

        service = MockEmailService()

        with caplog.at_level(logging.INFO):
            result = await service.send_password_reset(
                to_email="user@example.com",
                reset_link="https://app.com/reset?token=abc123",
                display_name="Test User",
            )

        assert result is True
        assert "user@example.com" in caplog.text
        assert "reset" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_mock_email_service_logs_approval_notification(self, caplog):
        """Mock service should log approval notification instead of sending."""
        from app.services.email_service import MockEmailService

        service = MockEmailService()

        with caplog.at_level(logging.INFO):
            result = await service.send_approval_notification(
                to_email="user@example.com",
                display_name="Test User",
                approved=True,
            )

        assert result is True
        assert "user@example.com" in caplog.text
        assert "approved" in caplog.text.lower()


class TestEmailServiceInterface:
    """Tests to verify interface compliance."""

    def test_mock_email_service_implements_interface(self):
        """MockEmailService should implement EmailServiceInterface."""
        from app.services.email_service import (
            MockEmailService,
            EmailServiceInterface,
        )

        service = MockEmailService()
        assert isinstance(service, EmailServiceInterface)
        assert hasattr(service, "send_password_reset")
        assert hasattr(service, "send_approval_notification")

    def test_azure_email_service_implements_interface(self):
        """AzureCommunicationEmailService should implement EmailServiceInterface."""
        from app.services.email_service import (
            AzureCommunicationEmailService,
            EmailServiceInterface,
        )

        service = AzureCommunicationEmailService(
            connection_string="endpoint=https://test.com/;accesskey=test",
            sender="test@test.com",
        )
        assert isinstance(service, EmailServiceInterface)
        assert hasattr(service, "send_password_reset")
        assert hasattr(service, "send_approval_notification")


class TestAzureEmailService:
    """Tests for AzureCommunicationEmailService."""

    @pytest.mark.asyncio
    async def test_azure_email_service_returns_false_when_send_fails(self):
        """Should return False and log error when email send fails."""
        from app.services.email_service import AzureCommunicationEmailService

        service = AzureCommunicationEmailService(
            connection_string="endpoint=https://test.com/;accesskey=test",
            sender="test@test.com",
        )

        # Mock the EmailClient to raise an exception
        with patch(
            "app.services.email_service.EmailClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.begin_send.side_effect = Exception("Network error")
            mock_client_class.from_connection_string.return_value = mock_client

            result = await service.send_password_reset(
                to_email="user@example.com",
                reset_link="https://app.com/reset?token=abc",
                display_name="Test User",
            )

        assert result is False
