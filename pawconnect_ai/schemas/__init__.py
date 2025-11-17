"""Data schemas and models for PawConnect AI."""

from .user_profile import UserProfile, UserPreferences
from .pet_data import Pet, PetProfile, PetMatch

__all__ = [
    "UserProfile",
    "UserPreferences",
    "Pet",
    "PetProfile",
    "PetMatch",
]
