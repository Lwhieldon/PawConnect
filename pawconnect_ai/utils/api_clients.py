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

        # CRITICAL: Filter to only "Available" status pets
        filters.append({
            "fieldName": "statuses.name",
            "operation": "equals",
            "criteria": "Available"
        })

        # Add species filter if provided
        if pet_type:
            # Map common pet types to species names
            species_map = {
                "dog": "Dog",
                "dogs": "Dog",
                "cat": "Cat",
                "cats": "Cat",
                "rabbit": "Rabbit",
                "rabbits": "Rabbit",
                "bird": "Bird",
                "birds": "Bird"
            }
            species_name = species_map.get(pet_type.lower(), pet_type.capitalize())
            filters.append({
                "fieldName": "species.singular",
                "operation": "equals",
                "criteria": species_name
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
                    "createdDate", "updatedDate",
                    "slug", "url",  # Add slug and url fields for linking
                    # Health and medical fields
                    "isSpecialNeeds", "specialNeedsDescription", "isMicrochipped",
                    "isHousetrained", "qualities", "activityLevel",
                    "fenceNeeded", "isHasAllergies", "isGoodWithCats", "isGoodWithDogs",
                    "isGoodWithKids", "ownerExperience"
                ],
                "orgs": ["name", "email", "phone", "street", "city", "state", "postalcode", "url", "website"]
            },
            "limit": str(min(limit, 250)),  # RescueGroups max is 250
            "page": str(page),
            "sort": [{"field": "animals.id", "direction": "asc"}]  # Add sort parameter
        }

        # Add location filtering using filterRadius (v5 API format)
        if location:
            import re
            is_zip = bool(re.match(r'^\d{5}(-\d{4})?$', location.strip()))

            if is_zip:
                # RescueGroups API v5 uses filterRadius object for location-based searches
                # Note: Some API endpoints may not support filterRadius in public search
                request_body["filterRadius"] = {
                    "postalcode": location.strip(),
                    "miles": str(distance)  # Convert to string for API compatibility
                }
                logger.info(f"Searching within {distance} miles of ZIP code {location}")
                logger.debug(f"filterRadius: {request_body['filterRadius']}")
            else:
                # Not a ZIP code - search all locations
                logger.info(f"Location '{location}' is not a ZIP code. Searching all locations. For location-specific results, please provide a 5-digit ZIP code.")

        # Log request for debugging
        api_url = f"{self.base_url}/public/animals/search/available"
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
        """
        Get details for a specific pet by ID using the RescueGroups API v5 GET endpoint.

        Args:
            pet_id: The pet ID to look up

        Returns:
            Pet details from RescueGroups API in format:
            {
                "data": {
                    "id": "...",
                    "type": "animals",
                    "attributes": {...}
                },
                "included": [...]
            }
            Or empty/error result if not found
        """
        await self.rate_limiter.acquire()

        headers = self._get_headers()

        # RescueGroups API v5 uses GET /public/animals/{id} for single pet lookup
        # Documentation: https://api.rescuegroups.org/v5/public/docs
        api_url = f"{self.base_url}/public/animals/{pet_id}"

        # Add include parameter to fetch organization data
        params = {
            "include": "orgs,breeds,species,colors,patterns,statuses"
        }

        logger.info(f"Fetching pet with ID: {pet_id}")
        logger.debug(f"RescueGroups GET {api_url} with params: {params}")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=settings.api_timeout),
            ) as response:
                if response.status == 404:
                    # Pet not found - return empty result
                    logger.info(f"Pet {pet_id} not found (404)")
                    return {"data": None}

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"RescueGroups API error for pet {pet_id}: {response.status}, "
                        f"response: {error_text}"
                    )
                    # Return empty result instead of raising error
                    return {"data": None}

                result = await response.json()

                # Log the result for debugging
                # RescueGroups GET endpoint returns {"data": {...}, "included": [...]}
                # where data is a SINGLE object (not an array)
                if result.get("data"):
                    pet_data = result["data"]

                    # Check if it's an array (shouldn't be for GET, but handle it)
                    if isinstance(pet_data, list):
                        logger.warning(f"GET endpoint returned array instead of object")
                        if len(pet_data) == 0:
                            logger.info(f"get_pet({pet_id}) returned empty array")
                            return {"data": None}
                        # Take first item
                        pet_data = pet_data[0]
                        # Update result to have single object
                        result["data"] = pet_data

                    returned_id = pet_data.get("id")
                    attributes = pet_data.get("attributes", {})
                    pet_name = attributes.get("name", "Unknown")
                    species = attributes.get("species", attributes.get("speciesid", "Unknown"))

                    # Log available attributes for debugging
                    logger.debug(f"Available attributes for pet {pet_id}: {list(attributes.keys())}")

                    logger.info(
                        f"get_pet({pet_id}) found: {pet_name} (ID: {returned_id}, Species: {species})"
                    )

                    # Verify we got the correct pet
                    if returned_id and str(returned_id) != str(pet_id):
                        logger.error(
                            f"API returned wrong pet! Requested: {pet_id}, Got: {returned_id}"
                        )
                        return {"data": None}
                else:
                    logger.info(f"get_pet({pet_id}) returned no data")

                return result

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
