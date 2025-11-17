"""
User profile and preferences data models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator


class HomeType(str, Enum):
    """Types of homes."""
    HOUSE = "house"
    APARTMENT = "apartment"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    FARM = "farm"
    OTHER = "other"


class ExperienceLevel(str, Enum):
    """Pet ownership experience levels."""
    FIRST_TIME = "first_time"
    SOME_EXPERIENCE = "some_experience"
    EXPERIENCED = "experienced"
    EXPERT = "expert"


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


class UserPreferences(BaseModel):
    """User preferences for pet matching."""

    pet_type: PetType = Field(..., description="Preferred type of pet")
    pet_size: Optional[List[PetSize]] = Field(
        default=None,
        description="Preferred pet sizes"
    )
    pet_age: Optional[List[PetAge]] = Field(
        default=None,
        description="Preferred pet ages"
    )

    # Lifestyle factors
    has_children: bool = Field(default=False, description="Has children at home")
    children_ages: Optional[List[int]] = Field(
        default=None,
        description="Ages of children"
    )
    has_other_pets: bool = Field(default=False, description="Has other pets")
    other_pets: Optional[List[str]] = Field(
        default=None,
        description="Types of other pets"
    )

    # Home characteristics
    home_type: HomeType = Field(..., description="Type of home")
    has_yard: bool = Field(default=False, description="Has yard or outdoor space")
    yard_fenced: bool = Field(default=False, description="Yard is fenced")

    # Work and availability
    work_schedule: str = Field(
        default="full_time",
        description="Work schedule: full_time, part_time, remote, retired"
    )
    hours_alone: int = Field(
        default=8,
        ge=0,
        le=24,
        description="Hours pet would be alone per day"
    )

    # Experience and preferences
    experience_level: ExperienceLevel = Field(
        ...,
        description="Pet ownership experience level"
    )
    breed_preferences: Optional[List[str]] = Field(
        default=None,
        description="Preferred breeds"
    )

    # Requirements and constraints
    good_with_children: Optional[bool] = Field(
        default=None,
        description="Must be good with children"
    )
    good_with_dogs: Optional[bool] = Field(
        default=None,
        description="Must be good with dogs"
    )
    good_with_cats: Optional[bool] = Field(
        default=None,
        description="Must be good with cats"
    )
    hypoallergenic: bool = Field(
        default=False,
        description="Needs hypoallergenic breed"
    )
    house_trained: bool = Field(
        default=False,
        description="Must be house trained"
    )
    special_needs_ok: bool = Field(
        default=False,
        description="Willing to adopt special needs pet"
    )

    # Activity level
    activity_level: str = Field(
        default="moderate",
        description="Preferred activity level: low, moderate, high"
    )
    exercise_commitment: int = Field(
        default=30,
        ge=0,
        description="Minutes per day can commit to exercise"
    )

    @validator("children_ages")
    def validate_children_ages(cls, v, values):
        """Validate children ages are provided when has_children is True."""
        if values.get("has_children") and not v:
            raise ValueError("children_ages required when has_children is True")
        return v


class UserProfile(BaseModel):
    """Complete user profile."""

    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")

    # Personal information
    first_name: str = Field(..., min_length=1, description="First name")
    last_name: str = Field(..., min_length=1, description="Last name")
    phone: Optional[str] = Field(default=None, description="Phone number")

    # Location
    address: Optional[str] = Field(default=None, description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., min_length=2, max_length=2, description="State code")
    zip_code: str = Field(..., description="ZIP code")
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    # Preferences
    preferences: UserPreferences = Field(..., description="Pet preferences")

    # Application status
    is_adopter: bool = Field(default=False, description="Looking to adopt")
    is_foster: bool = Field(default=False, description="Looking to foster")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # History
    viewed_pets: List[str] = Field(
        default_factory=list,
        description="IDs of pets viewed"
    )
    favorited_pets: List[str] = Field(
        default_factory=list,
        description="IDs of favorited pets"
    )
    application_ids: List[str] = Field(
        default_factory=list,
        description="IDs of submitted applications"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_12345",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1-206-555-0123",
                "city": "Seattle",
                "state": "WA",
                "zip_code": "98101",
                "preferences": {
                    "pet_type": "dog",
                    "pet_size": ["medium", "large"],
                    "home_type": "house",
                    "has_yard": True,
                    "experience_level": "some_experience"
                },
                "is_adopter": True
            }
        }
