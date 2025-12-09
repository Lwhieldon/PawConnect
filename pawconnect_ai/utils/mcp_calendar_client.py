"""
MCP Calendar Client - Multi-provider calendar support
Provides unified interface for calendar operations via Google Calendar or Outlook MCP servers.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..config import settings


class MCPCalendarClient:
    """
    Unified calendar client supporting multiple MCP calendar providers.
    Automatically selects provider based on configuration.
    """

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize MCP calendar client.

        Args:
            provider: Calendar provider (google-calendar, outlook). If None, uses config default.
        """
        self.provider = provider or settings.mcp_calendar_provider
        self.enabled = settings.mcp_calendar_enabled

        if not self.enabled:
            logger.warning("MCP calendar is disabled in configuration")

        # Provider-specific configuration
        self.provider_config = self._get_provider_config()

        logger.info(f"MCP Calendar Client initialized with provider: {self.provider}")

    def _get_provider_config(self) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        if self.provider == "google-calendar":
            return {
                "calendar_id": settings.google_calendar_id,
                "client_id": settings.google_calendar_client_id,
                "client_secret": settings.google_calendar_client_secret,
                "refresh_token": settings.google_calendar_refresh_token,
            }
        elif self.provider == "outlook":
            return {
                "client_id": settings.outlook_client_id,
                "client_secret": settings.outlook_client_secret,
                "refresh_token": settings.outlook_refresh_token,
                "tenant_id": settings.outlook_tenant_id,
            }
        else:
            logger.error(f"Unknown calendar provider: {self.provider}")
            return {}

    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a calendar event.

        Args:
            summary: Event title/summary
            start_time: Event start datetime
            end_time: Event end datetime
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            reminders: List of reminder configurations

        Returns:
            Dictionary with event details including event_id
        """
        if not self.enabled:
            logger.warning("Calendar event creation skipped - MCP calendar disabled")
            return {"status": "disabled", "event_id": None}

        if settings.testing_mode or settings.mock_apis:
            logger.info(f"[MOCK] Creating calendar event: {summary}")
            return {
                "status": "success",
                "event_id": f"mock_event_{int(datetime.utcnow().timestamp())}",
                "provider": self.provider,
                "summary": summary,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            }

        try:
            # Prepare event data
            event_data = {
                "summary": summary,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "description": description,
                "location": location,
            }

            if attendees:
                event_data["attendees"] = [{"email": email} for email in attendees]

            if reminders:
                event_data["reminders"] = reminders
            else:
                # Default reminders: 24 hours and 1 hour before
                event_data["reminders"] = [
                    {"method": "email", "minutes": 1440},  # 24 hours
                    {"method": "popup", "minutes": 60},  # 1 hour
                ]

            # Create via provider-specific method
            if self.provider == "google-calendar":
                result = await self._create_google_event(event_data)
            elif self.provider == "outlook":
                result = await self._create_outlook_event(event_data)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Calendar event created successfully via {self.provider}: {summary}")
            return result

        except Exception as e:
            logger.error(f"Failed to create calendar event via {self.provider}: {e}")
            raise

    async def _create_google_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create event via Google Calendar MCP server."""
        logger.info("Creating event via Google Calendar MCP server")

        # Note: This is a placeholder for MCP server integration
        # TODO: Implement actual MCP server call when MCP servers are running

        return {
            "status": "success",
            "event_id": f"google_event_{int(datetime.utcnow().timestamp())}",
            "provider": "google-calendar",
            "summary": event_data["summary"],
            "start": event_data["start"],
            "end": event_data["end"],
            "html_link": f"https://calendar.google.com/calendar/event?eid=mock",
        }

    async def _create_outlook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create event via Outlook MCP server."""
        logger.info("Creating event via Outlook MCP server")

        # Note: This is a placeholder for MCP server integration
        # TODO: Implement actual MCP server call when MCP servers are running

        return {
            "status": "success",
            "event_id": f"outlook_event_{int(datetime.utcnow().timestamp())}",
            "provider": "outlook",
            "summary": event_data["summary"],
            "start": event_data["start"],
            "end": event_data["end"],
            "web_link": f"https://outlook.office365.com/calendar/item/mock",
        }

    async def get_events(
        self,
        start_time: datetime,
        end_time: datetime,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List calendar events within a time range.

        Args:
            start_time: Start of time range
            end_time: End of time range
            max_results: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        if not self.enabled:
            logger.warning("Calendar event listing skipped - MCP calendar disabled")
            return []

        if settings.testing_mode or settings.mock_apis:
            logger.info(f"[MOCK] Listing calendar events from {start_time} to {end_time}")
            return []

        try:
            if self.provider == "google-calendar":
                result = await self._list_google_events(start_time, end_time, max_results)
            elif self.provider == "outlook":
                result = await self._list_outlook_events(start_time, end_time, max_results)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Retrieved {len(result)} calendar events via {self.provider}")
            return result

        except Exception as e:
            logger.error(f"Failed to list calendar events via {self.provider}: {e}")
            return []

    async def _list_google_events(
        self, start_time: datetime, end_time: datetime, max_results: int
    ) -> List[Dict[str, Any]]:
        """List events via Google Calendar MCP server."""
        # TODO: Implement actual MCP server call
        return []

    async def _list_outlook_events(
        self, start_time: datetime, end_time: datetime, max_results: int
    ) -> List[Dict[str, Any]]:
        """List events via Outlook MCP server."""
        # TODO: Implement actual MCP server call
        return []

    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id: Event identifier
            updates: Dictionary of fields to update

        Returns:
            Updated event details
        """
        if not self.enabled:
            logger.warning("Calendar event update skipped - MCP calendar disabled")
            return {"status": "disabled"}

        if settings.testing_mode or settings.mock_apis:
            logger.info(f"[MOCK] Updating calendar event: {event_id}")
            return {
                "status": "success",
                "event_id": event_id,
                "provider": self.provider,
            }

        try:
            if self.provider == "google-calendar":
                result = await self._update_google_event(event_id, updates)
            elif self.provider == "outlook":
                result = await self._update_outlook_event(event_id, updates)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Calendar event updated successfully via {self.provider}: {event_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to update calendar event via {self.provider}: {e}")
            raise

    async def _update_google_event(self, event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update event via Google Calendar MCP server."""
        # TODO: Implement actual MCP server call
        return {"status": "success", "event_id": event_id, "provider": "google-calendar"}

    async def _update_outlook_event(self, event_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update event via Outlook MCP server."""
        # TODO: Implement actual MCP server call
        return {"status": "success", "event_id": event_id, "provider": "outlook"}

    async def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event.

        Args:
            event_id: Event identifier

        Returns:
            Deletion status
        """
        if not self.enabled:
            logger.warning("Calendar event deletion skipped - MCP calendar disabled")
            return {"status": "disabled"}

        if settings.testing_mode or settings.mock_apis:
            logger.info(f"[MOCK] Deleting calendar event: {event_id}")
            return {
                "status": "success",
                "event_id": event_id,
                "provider": self.provider,
            }

        try:
            if self.provider == "google-calendar":
                result = await self._delete_google_event(event_id)
            elif self.provider == "outlook":
                result = await self._delete_outlook_event(event_id)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Calendar event deleted successfully via {self.provider}: {event_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete calendar event via {self.provider}: {e}")
            raise

    async def _delete_google_event(self, event_id: str) -> Dict[str, Any]:
        """Delete event via Google Calendar MCP server."""
        # TODO: Implement actual MCP server call
        return {"status": "success", "event_id": event_id, "provider": "google-calendar"}

    async def _delete_outlook_event(self, event_id: str) -> Dict[str, Any]:
        """Delete event via Outlook MCP server."""
        # TODO: Implement actual MCP server call
        return {"status": "success", "event_id": event_id, "provider": "outlook"}

    async def create_visit_event(
        self,
        user_name: str,
        user_email: str,
        pet_name: str,
        pet_id: str,
        visit_datetime: datetime,
        duration_minutes: int,
        shelter_name: str,
        shelter_address: str,
        visit_id: str,
    ) -> Dict[str, Any]:
        """
        Create a calendar event for a shelter visit.

        Args:
            user_name: Name of the visitor
            user_email: Email of the visitor
            pet_name: Name of the pet
            pet_id: Pet identifier
            visit_datetime: Scheduled visit date/time
            duration_minutes: Visit duration in minutes
            shelter_name: Name of the shelter
            shelter_address: Address of the shelter
            visit_id: Visit confirmation ID

        Returns:
            Calendar event details
        """
        end_time = visit_datetime + timedelta(minutes=duration_minutes)

        summary = f"Meet {pet_name} at {shelter_name}"
        description = f"""
Shelter Visit Confirmation

Visitor: {user_name}
Pet: {pet_name} (ID: {pet_id})
Confirmation ID: {visit_id}

What to bring:
- Valid photo ID
- This confirmation ID
- Any questions about {pet_name}

Looking forward to seeing you!
        """.strip()

        return await self.create_event(
            summary=summary,
            start_time=visit_datetime,
            end_time=end_time,
            description=description,
            location=f"{shelter_name}, {shelter_address}",
            attendees=[user_email],
            reminders=[
                {"method": "email", "minutes": 1440},  # 24 hours before
                {"method": "popup", "minutes": 60},  # 1 hour before
            ],
        )


# Global client instance
_calendar_client: Optional[MCPCalendarClient] = None


def get_calendar_client(provider: Optional[str] = None) -> MCPCalendarClient:
    """Get or create global calendar client instance."""
    global _calendar_client
    if _calendar_client is None or (provider and provider != _calendar_client.provider):
        _calendar_client = MCPCalendarClient(provider=provider)
    return _calendar_client
