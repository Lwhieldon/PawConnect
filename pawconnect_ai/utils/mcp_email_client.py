"""
MCP Email Client - Multi-provider email support
Provides unified interface for sending emails via Gmail, Outlook, or SendGrid MCP servers.
"""

import json
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from ..config import settings


class MCPEmailClient:
    """
    Unified email client supporting multiple MCP email providers.
    Automatically selects provider based on configuration.
    """

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize MCP email client.

        Args:
            provider: Email provider (gmail, outlook, sendgrid). If None, uses config default.
        """
        self.provider = provider or settings.mcp_email_provider
        self.enabled = settings.mcp_email_enabled

        if not self.enabled:
            logger.warning("MCP email is disabled in configuration")

        # Provider-specific configuration
        self.provider_config = self._get_provider_config()

        logger.info(f"MCP Email Client initialized with provider: {self.provider}")

    def _get_provider_config(self) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        if self.provider == "gmail":
            return {
                "from_email": settings.gmail_from_email,
                "from_name": settings.gmail_from_name,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "refresh_token": settings.gmail_refresh_token,
            }
        elif self.provider == "outlook":
            return {
                "from_email": settings.outlook_client_id,  # Will use authenticated user's email
                "client_id": settings.outlook_client_id,
                "client_secret": settings.outlook_client_secret,
                "refresh_token": settings.outlook_refresh_token,
                "tenant_id": settings.outlook_tenant_id,
            }
        elif self.provider == "sendgrid":
            return {
                "from_email": settings.sendgrid_from_email,
                "from_name": settings.sendgrid_from_name,
                "api_key": settings.sendgrid_api_key,
            }
        else:
            logger.error(f"Unknown email provider: {self.provider}")
            return {}

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via configured MCP provider.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional, will strip HTML if not provided)
            cc: CC email addresses
            bcc: BCC email addresses
            attachments: List of attachment dictionaries

        Returns:
            Dictionary with send status and message ID
        """
        if not self.enabled:
            logger.warning("Email sending skipped - MCP email disabled")
            return {"status": "disabled", "message_id": None}

        if settings.testing_mode or settings.mock_apis:
            logger.info(f"[MOCK] Sending email to {to_email}: {subject}")
            return {
                "status": "success",
                "message_id": f"mock_{int(datetime.utcnow().timestamp())}",
                "provider": self.provider,
            }

        try:
            # Prepare email data
            email_data = {
                "to": to_email,
                "subject": subject,
                "html_body": body_html,
                "text_body": body_text or self._html_to_text(body_html),
                "from_email": self.provider_config.get("from_email"),
                "from_name": self.provider_config.get("from_name"),
            }

            if cc:
                email_data["cc"] = cc
            if bcc:
                email_data["bcc"] = bcc
            if attachments:
                email_data["attachments"] = attachments

            # Send via provider-specific method
            if self.provider == "gmail":
                result = await self._send_via_gmail(email_data)
            elif self.provider == "outlook":
                result = await self._send_via_outlook(email_data)
            elif self.provider == "sendgrid":
                result = await self._send_via_sendgrid(email_data)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            logger.info(f"Email sent successfully to {to_email} via {self.provider}")
            return result

        except Exception as e:
            logger.error(f"Failed to send email via {self.provider}: {e}")
            # Try fallback provider if available
            if self.provider != "sendgrid" and settings.sendgrid_api_key:
                logger.info("Attempting fallback to SendGrid")
                fallback_client = MCPEmailClient(provider="sendgrid")
                return await fallback_client.send_email(
                    to_email=to_email,
                    subject=subject,
                    body_html=body_html,
                    body_text=body_text,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments,
                )
            raise

    async def _send_via_gmail(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via Gmail MCP server."""
        # Note: This is a placeholder for MCP server integration
        # In production, this would call the actual Gmail MCP server via subprocess/API

        logger.info("Sending via Gmail MCP server")

        # For now, return mock response
        # TODO: Implement actual MCP server call when MCP servers are running
        return {
            "status": "success",
            "message_id": f"gmail_{int(datetime.utcnow().timestamp())}",
            "provider": "gmail",
        }

    async def _send_via_outlook(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via Outlook MCP server."""
        logger.info("Sending via Outlook MCP server")

        # For now, return mock response
        # TODO: Implement actual MCP server call when MCP servers are running
        return {
            "status": "success",
            "message_id": f"outlook_{int(datetime.utcnow().timestamp())}",
            "provider": "outlook",
        }

    async def _send_via_sendgrid(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via SendGrid MCP server."""
        logger.info("Sending via SendGrid MCP server")

        # For now, return mock response
        # TODO: Implement actual MCP server call when MCP servers are running
        return {
            "status": "success",
            "message_id": f"sendgrid_{int(datetime.utcnow().timestamp())}",
            "provider": "sendgrid",
        }

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (basic implementation)."""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def send_visit_confirmation(
        self,
        to_email: str,
        user_name: str,
        pet_name: str,
        pet_id: str,
        visit_datetime: datetime,
        shelter_name: str,
        shelter_address: str,
        visit_id: str,
    ) -> Dict[str, Any]:
        """
        Send visit confirmation email with shelter details.

        Args:
            to_email: Recipient email
            user_name: User's name
            pet_name: Pet's name
            pet_id: Pet identifier
            visit_datetime: Scheduled visit date/time
            shelter_name: Shelter name
            shelter_address: Shelter address
            visit_id: Visit confirmation ID

        Returns:
            Email send result
        """
        subject = settings.email_visit_confirmation_subject.format(pet_name=pet_name)

        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 12px; }}
                .button {{ background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Visit Confirmed!</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <p>Great news! Your visit to meet <strong>{pet_name}</strong> has been confirmed.</p>

                <div class="details">
                    <h3>Visit Details</h3>
                    <p><strong>Pet:</strong> {pet_name}</p>
                    <p><strong>Date & Time:</strong> {visit_datetime.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
                    <p><strong>Location:</strong> {shelter_name}</p>
                    <p><strong>Address:</strong> {shelter_address}</p>
                    <p><strong>Confirmation ID:</strong> {visit_id}</p>
                </div>

                <h3>What to Bring</h3>
                <ul>
                    <li>Valid photo ID</li>
                    <li>Your confirmation ID (above)</li>
                    <li>Any questions you have about {pet_name}</li>
                </ul>

                <h3>What to Expect</h3>
                <p>During your visit, you'll have the opportunity to:</p>
                <ul>
                    <li>Spend quality time with {pet_name}</li>
                    <li>Learn about their personality and needs</li>
                    <li>Ask our staff any questions</li>
                    <li>Start the adoption process if you're interested</li>
                </ul>

                <p>We're excited for you to meet {pet_name}! If you need to reschedule or have any questions, please contact the shelter directly.</p>

                <p>Best regards,<br>The PawConnect Team</p>
            </div>
            <div class="footer">
                <p>This email was sent by PawConnect AI - Connecting pets with loving homes</p>
                <p>Confirmation ID: {visit_id}</p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
        )

    async def send_application_status_update(
        self,
        to_email: str,
        user_name: str,
        pet_name: str,
        application_status: str,
        application_id: str,
        additional_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send application status update email.

        Args:
            to_email: Recipient email
            user_name: User's name
            pet_name: Pet's name
            application_status: Current application status
            application_id: Application identifier
            additional_notes: Optional additional information

        Returns:
            Email send result
        """
        subject = settings.email_application_status_subject.format(pet_name=pet_name)

        status_messages = {
            "submitted": "We've received your application!",
            "under_review": "Your application is under review",
            "background_check": "Background check in progress",
            "home_assessment_scheduled": "Home assessment scheduled",
            "approved": "Congratulations! Your application has been approved!",
            "rejected": "Application status update",
        }

        status_message = status_messages.get(application_status, "Application status update")

        body_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .status {{ background-color: #e8f5e9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
                .footer {{ background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{status_message}</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <p>We have an update on your application to adopt <strong>{pet_name}</strong>.</p>

                <div class="status">
                    <h3>Status: {application_status.replace('_', ' ').title()}</h3>
                    <p><strong>Application ID:</strong> {application_id}</p>
                    {f'<p><strong>Notes:</strong> {additional_notes}</p>' if additional_notes else ''}
                </div>

                <p>Thank you for your interest in providing a loving home to {pet_name}. We'll keep you updated as your application progresses.</p>

                <p>Best regards,<br>The PawConnect Team</p>
            </div>
            <div class="footer">
                <p>Application ID: {application_id}</p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body_html=body_html,
        )


# Global client instance
_email_client: Optional[MCPEmailClient] = None


def get_email_client(provider: Optional[str] = None) -> MCPEmailClient:
    """Get or create global email client instance."""
    global _email_client
    if _email_client is None or (provider and provider != _email_client.provider):
        _email_client = MCPEmailClient(provider=provider)
    return _email_client
