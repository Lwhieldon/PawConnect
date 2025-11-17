"""
Pet data models and schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class PetType(str, Enum):
    """Types of pets."""
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"
    SMALL_FURRY = "small_furry"
    SCALES_FINS_OTHER = "scales_fins_other"


class PetSize(str, Enum):
    """Pet size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class PetAge(str, Enum):
    """Pet age categories."""
    BABY = "baby"
    YOUNG = "young"
    ADULT = "adult"
    SENIOR = "senior"


class Gender(str, Enum):
    """Pet gender."""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class CoatLength(str, Enum):
    """Coat length categories."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    HAIRLESS = "hairless"


class PetStatus(str, Enum):
    """Pet availability status."""
    AVAILABLE = "available"
    PENDING = "pending"
    ADOPTED = "adopted"
    FOSTERED = "fostered"


class PetAttributes(BaseModel):
    """Pet behavioral and physical attributes."""

    # Behavioral traits
    good_with_children: Optional[bool] = Field(default=None)
    good_with_dogs: Optional[bool] = Field(default=None)
    good_with_cats: Optional[bool] = Field(default=None)

    # Training and behavior
    house_trained: bool = Field(default=False)
    declawed: bool = Field(default=False)
    spayed_neutered: bool = Field(default=False)

    # Special characteristics
    special_needs: bool = Field(default=False)
    shots_current: bool = Field(default=True)

    # Personality
    energy_level: str = Field(
        default="moderate",
        description="Energy level: low, moderate, high"
    )
    temperament: List[str] = Field(
        default_factory=list,
        description="Personality traits"
    )


class ShelterInfo(BaseModel):
    """Information about the shelter or rescue."""

    organization_id: str = Field(..., description="Shelter/rescue organization ID")
    name: str = Field(..., description="Organization name")

    # Contact information
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    website: Optional[HttpUrl] = Field(default=None)

    # Location
    address: Optional[str] = Field(default=None)
    city: str = Field(...)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(...)

    # Coordinates
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class PetPhoto(BaseModel):
    """Pet photo information."""

    url: HttpUrl = Field(..., description="Photo URL")
    small: Optional[HttpUrl] = Field(default=None, description="Small thumbnail URL")
    medium: Optional[HttpUrl] = Field(default=None, description="Medium thumbnail URL")
    large: Optional[HttpUrl] = Field(default=None, description="Large thumbnail URL")
    full: Optional[HttpUrl] = Field(default=None, description="Full size URL")


class VisionAnalysis(BaseModel):
    """Computer vision analysis results."""

    # Breed detection
    detected_breeds: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detected breeds with confidence scores"
    )
    primary_breed: Optional[str] = Field(default=None)
    breed_confidence: Optional[float] = Field(default=None, ge=0, le=1)

    # Age estimation
    estimated_age: Optional[str] = Field(default=None)
    age_confidence: Optional[float] = Field(default=None, ge=0, le=1)

    # Visual features
    coat_color: Optional[List[str]] = Field(default=None)
    coat_pattern: Optional[str] = Field(default=None)
    visible_health_markers: List[str] = Field(default_factory=list)

    # Behavioral cues
    emotional_state: Optional[str] = Field(
        default=None,
        description="Detected emotional state: friendly, fearful, energetic, calm"
    )

    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: str = Field(default="1.0")


class Pet(BaseModel):
    """Complete pet profile."""

    # Identifiers
    pet_id: str = Field(..., description="Unique pet identifier")
    external_id: Optional[str] = Field(
        default=None,
        description="External system ID (e.g., Petfinder ID)"
    )

    # Basic information
    name: str = Field(..., description="Pet name")
    species: PetType = Field(..., description="Species/type")
    breed: Optional[str] = Field(default=None, description="Primary breed")
    mixed_breed: bool = Field(default=False)
    secondary_breed: Optional[str] = Field(default=None)

    # Physical characteristics
    age: PetAge = Field(..., description="Age category")
    age_numeric: Optional[int] = Field(
        default=None,
        ge=0,
        description="Age in months"
    )
    size: PetSize = Field(..., description="Size category")
    gender: Gender = Field(..., description="Gender")
    color: Optional[str] = Field(default=None, description="Primary color")
    coat: Optional[CoatLength] = Field(default=None, description="Coat length")

    # Attributes and behavior
    attributes: PetAttributes = Field(
        default_factory=PetAttributes,
        description="Behavioral attributes"
    )

    # Description
    description: str = Field(
        default="",
        description="Detailed description"
    )
    story: Optional[str] = Field(
        default=None,
        description="Pet's story or background"
    )

    # Media
    photos: List[PetPhoto] = Field(
        default_factory=list,
        description="Pet photos"
    )
    primary_photo_url: Optional[HttpUrl] = Field(default=None)

    # Vision analysis
    vision_analysis: Optional[VisionAnalysis] = Field(default=None)

    # Shelter information
    shelter: ShelterInfo = Field(..., description="Shelter/rescue information")

    # Availability
    status: PetStatus = Field(
        default=PetStatus.AVAILABLE,
        description="Availability status"
    )
    published_at: Optional[datetime] = Field(default=None)
    days_in_shelter: Optional[int] = Field(default=None, ge=0)

    # Urgency factors
    is_urgent: bool = Field(
        default=False,
        description="Urgent placement needed"
    )
    urgency_reason: Optional[str] = Field(default=None)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_synced: Optional[datetime] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "pet_id": "pet_12345",
                "name": "Max",
                "species": "dog",
                "breed": "Labrador Retriever",
                "age": "adult",
                "size": "large",
                "gender": "male",
                "description": "Max is a friendly and energetic dog...",
                "shelter": {
                    "organization_id": "shelter_001",
                    "name": "Seattle Animal Shelter",
                    "city": "Seattle",
                    "state": "WA",
                    "zip_code": "98101"
                }
            }
        }


class PetMatch(BaseModel):
    """Pet match with compatibility score and explanation."""

    pet: Pet = Field(..., description="Pet profile")

    # Matching scores
    overall_score: float = Field(..., ge=0, le=1, description="Overall compatibility score")
    lifestyle_score: float = Field(..., ge=0, le=1)
    personality_score: float = Field(..., ge=0, le=1)
    practical_score: float = Field(..., ge=0, le=1)
    urgency_boost: float = Field(default=0, ge=0, le=1)

    # Explanation
    match_explanation: str = Field(
        ...,
        description="Human-readable explanation of why this is a good match"
    )
    key_factors: List[str] = Field(
        default_factory=list,
        description="Key factors contributing to the match"
    )
    potential_concerns: List[str] = Field(
        default_factory=list,
        description="Potential concerns or considerations"
    )

    # Rankings
    rank: Optional[int] = Field(default=None, ge=1)

    # Metadata
    matched_at: datetime = Field(default_factory=datetime.utcnow)
    model_version: str = Field(default="1.0")

    class Config:
        json_schema_extra = {
            "example": {
                "pet": {"pet_id": "pet_12345", "name": "Max"},
                "overall_score": 0.87,
                "lifestyle_score": 0.92,
                "personality_score": 0.85,
                "practical_score": 0.84,
                "match_explanation": "Max is an excellent match because...",
                "key_factors": ["Good with children", "Low maintenance"],
                "rank": 1
            }
        }


class PetProfile(BaseModel):
    """Simplified pet profile for display."""

    pet_id: str
    name: str
    species: str
    breed: Optional[str] = None
    age: str
    size: str
    gender: str
    description: str
    photo_url: Optional[str] = None
    shelter_name: str
    city: str
    state: str
    distance_miles: Optional[float] = None
