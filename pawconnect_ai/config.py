"""
Configuration management for PawConnect AI.
Loads settings from environment variables and provides typed configuration access.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    environment: str = Field(default="development", description="Environment: development, staging, production")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Google Cloud Platform
    gcp_project_id: str = Field(default="pawconnect-ai", description="GCP Project ID")
    gcp_region: str = Field(default="us-central1", description="GCP Region")
    gcp_credentials_path: Optional[str] = Field(default=None, description="Path to GCP credentials JSON")

    # RescueGroups API
    rescuegroups_api_key: str = Field(default="", description="RescueGroups API Key")
    rescuegroups_base_url: str = Field(
        default="https://api.rescuegroups.org/v5",
        description="RescueGroups API base URL"
    )

    # Dialogflow CX
    dialogflow_agent_id: str = Field(default="", description="Dialogflow CX Agent ID")
    dialogflow_location: str = Field(default="us-central1", description="Dialogflow location")

    # Vertex AI
    vertex_ai_endpoint: str = Field(default="", description="Vertex AI model endpoint")
    vertex_ai_model_name: str = Field(
        default="recommendation-model",
        description="Vertex AI model name"
    )

    # Gemini AI (for ConversationAgent)
    # Note: Gemini 1.5 models retired April 2025, using Gemini 2.0
    gemini_model_name: str = Field(
        default="gemini-2.0-flash-001",
        description="Gemini model name for conversation understanding"
    )
    gemini_temperature: float = Field(
        default=0.7,
        description="Gemini model temperature (0.0-1.0)"
    )
    gemini_max_output_tokens: int = Field(
        default=1024,
        description="Maximum tokens for Gemini responses"
    )
    use_gemini_for_conversation: bool = Field(
        default=True,
        description="Use Gemini for conversation agent (fallback to keyword matching if False)"
    )

    # Cloud Vision API
    vision_api_enabled: bool = Field(default=True, description="Enable Cloud Vision API")

    # Cloud Pub/Sub
    pubsub_topic_prefix: str = Field(
        default="pawconnect",
        description="Pub/Sub topic prefix"
    )
    pubsub_search_topic: str = Field(
        default="pawconnect-search-results",
        description="Pub/Sub topic for search results"
    )
    pubsub_recommendation_topic: str = Field(
        default="pawconnect-recommendations",
        description="Pub/Sub topic for recommendations"
    )

    # Firestore
    firestore_collection_users: str = Field(
        default="users",
        description="Firestore collection for user profiles"
    )
    firestore_collection_applications: str = Field(
        default="applications",
        description="Firestore collection for applications"
    )
    firestore_collection_sessions: str = Field(
        default="sessions",
        description="Firestore collection for conversation sessions"
    )

    # Redis/Memorystore
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # API Settings
    api_timeout: int = Field(default=30, description="API request timeout in seconds")
    api_max_retries: int = Field(default=3, description="Maximum API retry attempts")
    api_rate_limit: int = Field(default=100, description="API rate limit per minute")

    # Search Settings
    default_search_radius: int = Field(default=50, description="Default search radius in miles")
    max_search_results: int = Field(default=100, description="Maximum search results")

    # Recommendation Settings
    recommendation_top_k: int = Field(default=10, description="Number of top recommendations")
    recommendation_min_score: float = Field(
        default=0.5,
        description="Minimum recommendation score threshold"
    )

    # Model Settings
    model_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum model confidence threshold"
    )

    # Testing
    testing_mode: bool = Field(default=False, description="Enable testing mode")
    mock_apis: bool = Field(default=False, description="Use mock API responses")

    # MCP Servers - Email & Calendar
    mcp_email_provider: str = Field(default="gmail", description="Email provider: gmail, outlook, sendgrid")
    mcp_calendar_provider: str = Field(default="google-calendar", description="Calendar provider: google-calendar, outlook")
    mcp_email_enabled: bool = Field(default=True, description="Enable MCP email functionality")
    mcp_calendar_enabled: bool = Field(default=True, description="Enable MCP calendar functionality")

    # Gmail MCP
    gmail_client_id: Optional[str] = Field(default=None, description="Gmail OAuth client ID")
    gmail_client_secret: Optional[str] = Field(default=None, description="Gmail OAuth client secret")
    gmail_redirect_uri: str = Field(default="http://localhost:8080/oauth/callback", description="Gmail OAuth redirect URI")
    gmail_refresh_token: Optional[str] = Field(default=None, description="Gmail OAuth refresh token")
    gmail_from_email: str = Field(default="noreply@pawconnect.org", description="Gmail sender email")
    gmail_from_name: str = Field(default="PawConnect Team", description="Gmail sender name")

    # Google Calendar MCP
    google_calendar_client_id: Optional[str] = Field(default=None, description="Google Calendar OAuth client ID")
    google_calendar_client_secret: Optional[str] = Field(default=None, description="Google Calendar OAuth client secret")
    google_calendar_redirect_uri: str = Field(default="http://localhost:8080/oauth/callback", description="Google Calendar OAuth redirect URI")
    google_calendar_refresh_token: Optional[str] = Field(default=None, description="Google Calendar OAuth refresh token")
    google_calendar_id: str = Field(default="primary", description="Google Calendar ID for shelter visits")

    # Outlook MCP
    outlook_client_id: Optional[str] = Field(default=None, description="Outlook/Microsoft365 OAuth client ID")
    outlook_client_secret: Optional[str] = Field(default=None, description="Outlook OAuth client secret")
    outlook_redirect_uri: str = Field(default="http://localhost:8080/oauth/callback", description="Outlook OAuth redirect URI")
    outlook_refresh_token: Optional[str] = Field(default=None, description="Outlook OAuth refresh token")
    outlook_tenant_id: str = Field(default="common", description="Microsoft tenant ID")

    # SendGrid MCP
    sendgrid_api_key: Optional[str] = Field(default=None, description="SendGrid API key")
    sendgrid_from_email: str = Field(default="noreply@pawconnect.org", description="SendGrid sender email")
    sendgrid_from_name: str = Field(default="PawConnect Team", description="SendGrid sender name")

    # Email Templates & Notifications
    email_visit_confirmation_subject: str = Field(
        default="Your Visit to Meet {pet_name} is Confirmed!",
        description="Subject for visit confirmation emails"
    )
    email_application_received_subject: str = Field(
        default="We Received Your {application_type} Application",
        description="Subject for application received emails"
    )
    email_application_status_subject: str = Field(
        default="Update on Your Application for {pet_name}",
        description="Subject for application status emails"
    )
    email_notify_visit_scheduled: bool = Field(default=True, description="Send email when visit is scheduled")
    email_notify_application_status: bool = Field(default=True, description="Send email on application status changes")
    email_notify_foster_adopter_match: bool = Field(default=True, description="Send email when foster/adopter match occurs")
    email_rate_limit: int = Field(default=100, description="Email rate limit per hour")

    def get_pubsub_topic(self, topic_name: str) -> str:
        """Get fully qualified Pub/Sub topic name."""
        return f"projects/{self.gcp_project_id}/topics/{topic_name}"

    def get_dialogflow_agent_path(self) -> str:
        """Get fully qualified Dialogflow agent path."""
        return (
            f"projects/{self.gcp_project_id}/"
            f"locations/{self.dialogflow_location}/"
            f"agents/{self.dialogflow_agent_id}"
        )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global _settings
    _settings = Settings()
    return _settings


# Convenience access
settings = get_settings()
