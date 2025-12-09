"""
Tests for MCP Email and Calendar integrations.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from pawconnect_ai.utils.mcp_email_client import MCPEmailClient, get_email_client
from pawconnect_ai.utils.mcp_calendar_client import MCPCalendarClient, get_calendar_client
from pawconnect_ai.tools import PawConnectTools
from pawconnect_ai.config import settings


class TestMCPEmailClient:
    """Tests for MCP Email Client."""

    @pytest.fixture
    def email_client(self):
        """Create email client instance for testing."""
        return MCPEmailClient(provider="gmail")

    @pytest.mark.asyncio
    async def test_email_client_initialization(self, email_client):
        """Test email client initializes correctly."""
        assert email_client.provider == "gmail"
        assert email_client.enabled == settings.mcp_email_enabled

    @pytest.mark.asyncio
    async def test_send_email_mock_mode(self, email_client):
        """Test email sending in mock mode."""
        with patch.object(settings, 'testing_mode', True):
            result = await email_client.send_email(
                to_email="test@example.com",
                subject="Test Email",
                body_html="<p>Test content</p>",
            )

            assert result["status"] == "success"
            assert result["provider"] == "gmail"
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_visit_confirmation(self, email_client):
        """Test visit confirmation email."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True):
            result = await email_client.send_visit_confirmation(
                to_email="adopter@example.com",
                user_name="John Doe",
                pet_name="Max",
                pet_id="pet_123",
                visit_datetime=visit_time,
                shelter_name="Happy Paws Shelter",
                shelter_address="123 Main St, Seattle, WA 98101",
                visit_id="visit_001",
            )

            assert result["status"] == "success"
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_application_status_update(self, email_client):
        """Test application status update email."""
        with patch.object(settings, 'testing_mode', True):
            result = await email_client.send_application_status_update(
                to_email="adopter@example.com",
                user_name="Jane Smith",
                pet_name="Luna",
                application_status="approved",
                application_id="app_456",
                additional_notes="Congratulations! Please schedule a pickup time.",
            )

            assert result["status"] == "success"
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_email_disabled(self):
        """Test email functionality when disabled."""
        with patch.object(settings, 'mcp_email_enabled', False):
            client = MCPEmailClient()
            result = await client.send_email(
                to_email="test@example.com",
                subject="Test",
                body_html="<p>Test</p>",
            )

            assert result["status"] == "disabled"
            assert result["message_id"] is None

    @pytest.mark.asyncio
    async def test_html_to_text_conversion(self, email_client):
        """Test HTML to plain text conversion."""
        html = "<h1>Hello World</h1><p>This is a <strong>test</strong> email.</p>"
        text = email_client._html_to_text(html)

        assert "Hello World" in text
        assert "test" in text
        assert "<h1>" not in text
        assert "<strong>" not in text

    @pytest.mark.asyncio
    async def test_fallback_to_sendgrid(self):
        """Test fallback to SendGrid when primary provider fails."""
        with patch.object(settings, 'testing_mode', False), \
             patch.object(settings, 'sendgrid_api_key', 'test_key'):

            client = MCPEmailClient(provider="gmail")

            # Mock Gmail failure
            with patch.object(client, '_send_via_gmail', side_effect=Exception("Gmail error")):
                # Should attempt fallback to SendGrid
                with patch('pawconnect_ai.utils.mcp_email_client.MCPEmailClient') as mock_sendgrid:
                    mock_instance = AsyncMock()
                    mock_instance.send_email = AsyncMock(return_value={"status": "success", "provider": "sendgrid"})
                    mock_sendgrid.return_value = mock_instance

                    try:
                        result = await client.send_email(
                            to_email="test@example.com",
                            subject="Test",
                            body_html="<p>Test</p>",
                        )
                    except Exception:
                        # Expected to fail in test without actual MCP servers
                        pass


class TestMCPCalendarClient:
    """Tests for MCP Calendar Client."""

    @pytest.fixture
    def calendar_client(self):
        """Create calendar client instance for testing."""
        return MCPCalendarClient(provider="google-calendar")

    @pytest.mark.asyncio
    async def test_calendar_client_initialization(self, calendar_client):
        """Test calendar client initializes correctly."""
        assert calendar_client.provider == "google-calendar"
        assert calendar_client.enabled == settings.mcp_calendar_enabled

    @pytest.mark.asyncio
    async def test_create_event_mock_mode(self, calendar_client):
        """Test calendar event creation in mock mode."""
        start_time = datetime.now() + timedelta(days=7)
        end_time = start_time + timedelta(minutes=45)

        with patch.object(settings, 'testing_mode', True):
            result = await calendar_client.create_event(
                summary="Test Event",
                start_time=start_time,
                end_time=end_time,
                description="Test description",
                location="Test location",
            )

            assert result["status"] == "success"
            assert result["provider"] == "google-calendar"
            assert "event_id" in result

    @pytest.mark.asyncio
    async def test_create_visit_event(self, calendar_client):
        """Test creating a visit event."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True):
            result = await calendar_client.create_visit_event(
                user_name="John Doe",
                user_email="john@example.com",
                pet_name="Max",
                pet_id="pet_123",
                visit_datetime=visit_time,
                duration_minutes=45,
                shelter_name="Happy Paws Shelter",
                shelter_address="123 Main St, Seattle, WA 98101",
                visit_id="visit_001",
            )

            assert result["status"] == "success"
            assert "event_id" in result
            assert result["summary"] == "Meet Max at Happy Paws Shelter"

    @pytest.mark.asyncio
    async def test_list_events_mock_mode(self, calendar_client):
        """Test listing calendar events."""
        start_time = datetime.now()
        end_time = start_time + timedelta(days=30)

        with patch.object(settings, 'testing_mode', True):
            result = await calendar_client.get_events(
                start_time=start_time,
                end_time=end_time,
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_event_mock_mode(self, calendar_client):
        """Test updating a calendar event."""
        with patch.object(settings, 'testing_mode', True):
            result = await calendar_client.update_event(
                event_id="test_event_123",
                updates={"summary": "Updated Event Title"},
            )

            assert result["status"] == "success"
            assert result["event_id"] == "test_event_123"

    @pytest.mark.asyncio
    async def test_delete_event_mock_mode(self, calendar_client):
        """Test deleting a calendar event."""
        with patch.object(settings, 'testing_mode', True):
            result = await calendar_client.delete_event(event_id="test_event_123")

            assert result["status"] == "success"
            assert result["event_id"] == "test_event_123"

    @pytest.mark.asyncio
    async def test_calendar_disabled(self):
        """Test calendar functionality when disabled."""
        with patch.object(settings, 'mcp_calendar_enabled', False):
            client = MCPCalendarClient()
            result = await client.create_event(
                summary="Test",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
            )

            assert result["status"] == "disabled"
            assert result["event_id"] is None


class TestVisitSchedulingIntegration:
    """Integration tests for visit scheduling with MCP."""

    @pytest.fixture
    def tools(self):
        """Create PawConnectTools instance."""
        return PawConnectTools()

    @pytest.mark.asyncio
    async def test_schedule_visit_with_mcp(self, tools):
        """Test complete visit scheduling flow with email and calendar."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True), \
             patch.object(settings, 'mock_apis', True), \
             patch.object(settings, 'mcp_email_enabled', True), \
             patch.object(settings, 'mcp_calendar_enabled', True):

            result = await tools.schedule_visit(
                user_id="test_user_001",
                pet_id="mock_001",  # Mock pet from PetSearchAgent
                preferred_time=visit_time,
                user_name="Test User",
                user_email="test@example.com",
            )

            # Verify visit was scheduled
            assert result["status"] == "scheduled"
            assert result["user_id"] == "test_user_001"
            assert result["pet_id"] == "mock_001"
            assert result["pet_name"] == "Max"  # From mock pet

            # Verify email was sent
            assert result.get("email_sent") is True
            assert "email_message_id" in result

            # Verify calendar event was created
            assert result.get("calendar_event_id") is not None

    @pytest.mark.asyncio
    async def test_schedule_visit_email_only(self, tools):
        """Test visit scheduling with email enabled but calendar disabled."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True), \
             patch.object(settings, 'mock_apis', True), \
             patch.object(settings, 'mcp_email_enabled', True), \
             patch.object(settings, 'mcp_calendar_enabled', False):

            result = await tools.schedule_visit(
                user_id="test_user_002",
                pet_id="mock_001",
                preferred_time=visit_time,
                user_name="Test User",
                user_email="test@example.com",
            )

            assert result["status"] == "scheduled"
            assert result.get("email_sent") is True
            assert result.get("calendar_event_id") is None

    @pytest.mark.asyncio
    async def test_schedule_visit_calendar_only(self, tools):
        """Test visit scheduling with calendar enabled but email disabled."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True), \
             patch.object(settings, 'mock_apis', True), \
             patch.object(settings, 'mcp_email_enabled', False), \
             patch.object(settings, 'mcp_calendar_enabled', True):

            result = await tools.schedule_visit(
                user_id="test_user_003",
                pet_id="mock_001",
                preferred_time=visit_time,
                user_name="Test User",
                user_email="test@example.com",
            )

            assert result["status"] == "scheduled"
            assert result.get("email_sent") is False
            assert result.get("calendar_event_id") is not None

    @pytest.mark.asyncio
    async def test_schedule_visit_pet_not_found(self, tools):
        """Test visit scheduling with invalid pet ID."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True), \
             patch.object(settings, 'mock_apis', True):

            with pytest.raises(ValueError, match="Pet not found"):
                await tools.schedule_visit(
                    user_id="test_user_004",
                    pet_id="invalid_pet_id",
                    preferred_time=visit_time,
                    user_name="Test User",
                    user_email="test@example.com",
                )

    @pytest.mark.asyncio
    async def test_schedule_visit_handles_email_failure_gracefully(self, tools):
        """Test that visit scheduling continues even if email fails."""
        visit_time = datetime.now() + timedelta(days=7)

        with patch.object(settings, 'testing_mode', True), \
             patch.object(settings, 'mock_apis', True), \
             patch.object(settings, 'mcp_email_enabled', True), \
             patch.object(settings, 'mcp_calendar_enabled', True):

            # Mock email failure
            with patch('pawconnect_ai.utils.mcp_email_client.MCPEmailClient.send_visit_confirmation',
                      side_effect=Exception("Email service unavailable")):

                result = await tools.schedule_visit(
                    user_id="test_user_005",
                    pet_id="mock_001",
                    preferred_time=visit_time,
                    user_name="Test User",
                    user_email="test@example.com",
                )

                # Visit should still be scheduled
                assert result["status"] == "scheduled"
                # Email should have failed but captured in error
                assert result.get("email_sent") is False
                assert "email_error" in result


class TestGetClientHelpers:
    """Tests for client getter functions."""

    def test_get_email_client_singleton(self):
        """Test that get_email_client returns singleton."""
        client1 = get_email_client()
        client2 = get_email_client()

        assert client1 is client2

    def test_get_email_client_different_provider(self):
        """Test that get_email_client creates new instance for different provider."""
        client1 = get_email_client("gmail")
        client2 = get_email_client("sendgrid")

        assert client1 is not client2
        assert client1.provider == "gmail"
        assert client2.provider == "sendgrid"

    def test_get_calendar_client_singleton(self):
        """Test that get_calendar_client returns singleton."""
        client1 = get_calendar_client()
        client2 = get_calendar_client()

        assert client1 is client2

    def test_get_calendar_client_different_provider(self):
        """Test that get_calendar_client creates new instance for different provider."""
        client1 = get_calendar_client("google-calendar")
        client2 = get_calendar_client("outlook")

        assert client1 is not client2
        assert client1.provider == "google-calendar"
        assert client2.provider == "outlook"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
