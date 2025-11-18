"""
External API clients for PawConnect AI.
Handles communication with RescueGroups, Google Cloud services, and other external APIs.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
import aiohttp
import requests
from loguru import logger

from ..config import settings
from ..schemas.pet_data import Pet, PetType


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]

        if len(self.calls) >= self.calls_per_minute:
            # Wait until oldest call is more than 60 seconds old
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                return await self.acquire()

        self.calls.append(now)


class RescueGroupsClient:
    """Client for RescueGroups API v5."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.rescuegroups_api_key
        self.base_url = base_url or settings.rescuegroups_base_url
        self.rate_limiter = RateLimiter(settings.api_rate_limit)

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers with authentication."""
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/vnd.api+json",
        }

    async def search_pets(
        self,
        pet_type: Optional[str] = None,
        location: Optional[str] = None,
        distance: int = 50,
        limit: int = 100,
        page: int = 1,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search for pets on RescueGroups.

        Args:
            pet_type: Type of pet (dog, cat, etc.)
            location: ZIP code or city, state
            distance: Search radius in miles
            limit: Number of results per page
            page: Page number
            **kwargs: Additional search parameters

        Returns:
            Search results from RescueGroups API
        """
        await self.rate_limiter.acquire()

        headers = self._get_headers()

        # Build RescueGroups API v5 request body
        filters = []

        # Species is included in the URL path, not as a filter
        species_path = f"/{pet_type}s" if pet_type else ""

        if location:
            # RescueGroups uses postal code for location filtering
            # Extract zip code from location (if it's "City, State" format, we need to handle it)
            zip_code = location
            if "," in location:
                # If location is "Seattle, WA", we can't use it directly
                # For now, skip location filter if not a zip code
                logger.warning(f"Location '{location}' is not a zip code. Skipping location filter. Please provide a 5-digit zip code for location filtering.")
            else:
                # Postal code filter
                filters.append({
                    "fieldName": "animalLocation",
                    "operation": "equals",
                    "criteria": zip_code
                })
                # Distance radius filter
                filters.append({
                    "fieldName": "animalLocationDistance",
                    "operation": "radius",
                    "criteria": str(distance)
                })

        # Build request body - v5 uses flat structure, not wrapped in "data"
        request_body = {
            "filters": filters,
            "filterProcessing": "1",  # Use AND logic
            "fields": {
                "animals": [
                    "name", "breedString", "breedPrimary", "breedSecondary",
                    "ageGroup", "ageString", "birthDate", "sex",
                    "sizeCurrent", "sizeUOM", "coatLength",
                    "descriptionText", "descriptionHtml",
                    "pictureThumbnailUrl", "pictureCount",
                    "isAdoptionPending", "priority", "rescueId",
                    "createdDate", "updatedDate"
                ],
                "orgs": ["name", "email", "phone", "street", "city", "state", "postalcode", "url"]
            },
            "limit": str(min(limit, 250)),  # RescueGroups max is 250
            "page": str(page)
        }

        # Log request for debugging
        api_url = f"{self.base_url}/public/animals/search/available{species_path}"
        logger.debug(f"RescueGroups API URL: {api_url}")
        logger.debug(f"RescueGroups API request: {request_body}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=request_body,
                timeout=aiohttp.ClientTimeout(total=settings.api_timeout),
            ) as response:
                if response.status != 200:
                    # Get error details
                    error_text = await response.text()
                    logger.error(
                        f"RescueGroups API error: {response.status}, "
                        f"message='{response.reason}', "
                        f"url='{response.url}', "
                        f"response='{error_text}'"
                    )
                response.raise_for_status()
                return await response.json()

    async def get_pet(self, pet_id: str) -> Dict[str, Any]:
        """Get details for a specific pet."""
        await self.rate_limiter.acquire()

        headers = self._get_headers()

        request_body = {
            "filters": [{
                "fieldName": "id",
                "operation": "equal",
                "criteria": pet_id
            }],
            "fields": {
                "animals": [
                    "name", "breedString", "breedPrimary", "breedSecondary",
                    "ageGroup", "ageString", "birthDate", "sex",
                    "sizeCurrent", "sizeUOM", "coatLength",
                    "descriptionText", "descriptionHtml",
                    "pictureThumbnailUrl", "pictureCount",
                    "isAdoptionPending", "priority", "rescueId",
                    "createdDate", "updatedDate"
                ],
                "orgs": ["name", "email", "phone", "street", "city", "state", "postalcode", "url"]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/public/animals/search",
                headers=headers,
                json=request_body,
                timeout=aiohttp.ClientTimeout(total=settings.api_timeout),
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def get_organizations(
        self, location: Optional[str] = None, limit: int = 100
    ) -> Dict[str, Any]:
        """Search for organizations/shelters."""
        await self.rate_limiter.acquire()

        headers = self._get_headers()

        filters = []
        if location:
            filters.append({
                "fieldName": "postalcode",
                "operation": "equal",
                "criteria": location
            })

        request_body = {
            "filters": filters if filters else [],
            "fields": {
                "orgs": [
                    "name", "email", "phone", "url",
                    "street", "city", "state", "postalcode",
                    "country"
                ]
            },
            "limit": str(min(limit, 250))
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/public/orgs/search",
                headers=headers,
                json=request_body,
                timeout=aiohttp.ClientTimeout(total=settings.api_timeout),
            ) as response:
                response.raise_for_status()
                return await response.json()


class GoogleCloudClient:
    """Client for Google Cloud services."""

    def __init__(self):
        """Initialize Google Cloud clients."""
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region

        # Lazy initialization of clients
        self._vision_client = None
        self._firestore_client = None
        self._pubsub_publisher = None
        self._pubsub_subscriber = None

    @property
    def vision_client(self):
        """Get or create Vision API client."""
        if self._vision_client is None:
            from google.cloud import vision

            self._vision_client = vision.ImageAnnotatorClient()
        return self._vision_client

    @property
    def firestore_client(self):
        """Get or create Firestore client."""
        if self._firestore_client is None:
            from google.cloud import firestore

            self._firestore_client = firestore.Client(project=self.project_id)
        return self._firestore_client

    @property
    def pubsub_publisher(self):
        """Get or create Pub/Sub publisher client."""
        if self._pubsub_publisher is None:
            from google.cloud import pubsub_v1

            self._pubsub_publisher = pubsub_v1.PublisherClient()
        return self._pubsub_publisher

    @property
    def pubsub_subscriber(self):
        """Get or create Pub/Sub subscriber client."""
        if self._pubsub_subscriber is None:
            from google.cloud import pubsub_v1

            self._pubsub_subscriber = pubsub_v1.SubscriberClient()
        return self._pubsub_subscriber

    async def analyze_image(self, image_uri: str) -> Dict[str, Any]:
        """
        Analyze an image using Google Cloud Vision API.

        Args:
            image_uri: URL or GCS URI of the image

        Returns:
            Vision API analysis results
        """
        from google.cloud import vision

        image = vision.Image()
        if image_uri.startswith("gs://"):
            image.source.image_uri = image_uri
        else:
            # For HTTP URLs, download and send content
            async with aiohttp.ClientSession() as session:
                async with session.get(image_uri) as response:
                    image.content = await response.read()

        # Perform multiple feature detections
        features = [
            vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION),
            vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION),
            vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES),
            vision.Feature(type_=vision.Feature.Type.SAFE_SEARCH_DETECTION),
        ]

        request = vision.AnnotateImageRequest(image=image, features=features)

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self.vision_client.annotate_image, request
        )

        return {
            "labels": [
                {"description": label.description, "score": label.score}
                for label in response.label_annotations
            ],
            "objects": [
                {"name": obj.name, "score": obj.score}
                for obj in response.localized_object_annotations
            ],
            "colors": [
                {
                    "color": {
                        "red": color.color.red,
                        "green": color.color.green,
                        "blue": color.color.blue,
                    },
                    "score": color.score,
                    "pixel_fraction": color.pixel_fraction,
                }
                for color in response.image_properties_annotation.dominant_colors.colors
            ],
            "safe_search": {
                "adult": response.safe_search_annotation.adult.name,
                "violence": response.safe_search_annotation.violence.name,
            },
        }

    async def publish_message(self, topic_name: str, message: Dict[str, Any]) -> str:
        """
        Publish a message to a Pub/Sub topic.

        Args:
            topic_name: Name of the topic
            message: Message data as dictionary

        Returns:
            Message ID
        """
        import json

        topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_name)

        message_json = json.dumps(message).encode("utf-8")

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        future = await loop.run_in_executor(
            None, self.pubsub_publisher.publish, topic_path, message_json
        )

        return future.result()

    def save_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Save user profile to Firestore."""
        collection = settings.firestore_collection_users
        doc_ref = self.firestore_client.collection(collection).document(user_id)
        doc_ref.set(profile)

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from Firestore."""
        collection = settings.firestore_collection_users
        doc_ref = self.firestore_client.collection(collection).document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        return None


# Singleton instances
rescuegroups_client = RescueGroupsClient()
google_cloud_client = GoogleCloudClient()
