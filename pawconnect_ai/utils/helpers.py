"""
Helper utilities for PawConnect AI.
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

from ..schemas.pet_data import Pet, PetProfile, ShelterInfo
from ..schemas.user_profile import UserProfile


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in miles
    """
    # Earth's radius in miles
    R = 3959.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def format_pet_profile(pet: Pet, user_location: Optional[tuple[float, float]] = None) -> PetProfile:
    """
    Format a Pet object into a simplified PetProfile for display.

    Args:
        pet: Full pet object
        user_location: Optional tuple of (latitude, longitude) for distance calculation

    Returns:
        Simplified PetProfile
    """
    distance_miles = None
    if user_location and pet.shelter.latitude and pet.shelter.longitude:
        distance_miles = calculate_distance(
            user_location[0],
            user_location[1],
            pet.shelter.latitude,
            pet.shelter.longitude,
        )
        distance_miles = round(distance_miles, 1)

    photo_url = None
    if pet.primary_photo_url:
        photo_url = str(pet.primary_photo_url)
    elif pet.photos:
        photo_url = str(pet.photos[0].url)

    return PetProfile(
        pet_id=pet.pet_id,
        name=pet.name,
        species=pet.species.value,
        breed=pet.breed,
        age=pet.age.value,
        size=pet.size.value,
        gender=pet.gender.value,
        description=pet.description[:500] if pet.description else "",
        photo_url=photo_url,
        shelter_name=pet.shelter.name,
        city=pet.shelter.city,
        state=pet.shelter.state,
        distance_miles=distance_miles,
    )


def calculate_age_in_months(age_category: str) -> int:
    """
    Estimate age in months from age category.

    Args:
        age_category: Age category (baby, young, adult, senior)

    Returns:
        Estimated age in months
    """
    age_map = {
        "baby": 6,  # 6 months
        "young": 18,  # 1.5 years
        "adult": 48,  # 4 years
        "senior": 96,  # 8 years
    }
    return age_map.get(age_category.lower(), 36)  # Default to 3 years


def calculate_urgency_score(pet: Pet) -> float:
    """
    Calculate urgency score for pet placement.

    Args:
        pet: Pet object

    Returns:
        Urgency score between 0 and 1
    """
    score = 0.0

    # Explicitly marked as urgent
    if pet.is_urgent:
        score += 0.4

    # Days in shelter (longer = more urgent)
    if pet.days_in_shelter:
        if pet.days_in_shelter > 180:  # 6+ months
            score += 0.3
        elif pet.days_in_shelter > 90:  # 3+ months
            score += 0.2
        elif pet.days_in_shelter > 30:  # 1+ month
            score += 0.1

    # Senior pets need homes faster
    if pet.age.value == "senior":
        score += 0.2

    # Special needs pets
    if pet.attributes.special_needs:
        score += 0.1

    return min(score, 1.0)


def format_match_explanation(
    pet: Pet,
    user: UserProfile,
    scores: Dict[str, float],
) -> tuple[str, List[str], List[str]]:
    """
    Generate human-readable match explanation.

    Args:
        pet: Pet object
        user: User profile
        scores: Dictionary of score components

    Returns:
        Tuple of (explanation, key_factors, potential_concerns)
    """
    key_factors = []
    concerns = []

    # Check compatibility factors
    prefs = user.preferences

    # Children compatibility
    if prefs.has_children:
        if pet.attributes.good_with_children:
            key_factors.append("Great with children")
        elif pet.attributes.good_with_children is False:
            concerns.append("May not be suitable for homes with children")

    # Pet compatibility
    if prefs.has_other_pets:
        if "dog" in [p.lower() for p in (prefs.other_pets or [])]:
            if pet.attributes.good_with_dogs:
                key_factors.append("Gets along well with dogs")
            elif pet.attributes.good_with_dogs is False:
                concerns.append("May not be compatible with your dog")

        if "cat" in [p.lower() for p in (prefs.other_pets or [])]:
            if pet.attributes.good_with_cats:
                key_factors.append("Gets along well with cats")
            elif pet.attributes.good_with_cats is False:
                concerns.append("May not be compatible with your cat")

    # Activity level
    if prefs.activity_level == "low" and pet.attributes.energy_level == "low":
        key_factors.append("Low energy level matches your lifestyle")
    elif prefs.activity_level == "high" and pet.attributes.energy_level == "high":
        key_factors.append("High energy level matches your active lifestyle")
    elif prefs.activity_level == "low" and pet.attributes.energy_level == "high":
        concerns.append("High energy pet may need more exercise than you can provide")

    # House trained
    if prefs.house_trained and pet.attributes.house_trained:
        key_factors.append("Already house trained")

    # Special needs
    if pet.attributes.special_needs:
        if prefs.special_needs_ok:
            key_factors.append("You're prepared for special needs care")
        else:
            concerns.append("Has special needs that may require extra care")

    # Home type
    if prefs.home_type.value == "apartment" and pet.size.value in ["small", "medium"]:
        key_factors.append("Size is appropriate for apartment living")
    elif prefs.home_type.value == "apartment" and pet.size.value in ["large", "extra_large"]:
        concerns.append("Large size may be challenging in an apartment")

    # Yard requirements
    if pet.species.value == "dog" and pet.size.value in ["large", "extra_large"]:
        if prefs.has_yard:
            key_factors.append("Your yard is perfect for a large dog")
        else:
            concerns.append("Large dogs typically need yard space")

    # Experience level
    if prefs.experience_level.value == "first_time":
        if pet.attributes.energy_level == "low" and pet.attributes.house_trained:
            key_factors.append("Good choice for first-time pet owner")
        elif pet.attributes.special_needs or pet.attributes.energy_level == "high":
            concerns.append("May be challenging for a first-time owner")

    # Build explanation
    overall_score = scores.get("overall_score", 0.5)

    if overall_score >= 0.8:
        intro = f"{pet.name} is an excellent match for you!"
    elif overall_score >= 0.6:
        intro = f"{pet.name} is a good match for you."
    else:
        intro = f"{pet.name} could be a potential match."

    explanation_parts = [intro]

    if key_factors:
        explanation_parts.append(
            "Key strengths: " + ", ".join(key_factors[:3]) + "."
        )

    if pet.is_urgent:
        explanation_parts.append(
            f"{pet.name} needs a home urgently and would benefit from quick placement."
        )

    explanation = " ".join(explanation_parts)

    return explanation, key_factors, concerns


def parse_petfinder_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse Petfinder API response into standardized format.

    Args:
        data: Raw Petfinder API response

    Returns:
        List of normalized pet data dictionaries
    """
    pets = []

    for animal in data.get("animals", []):
        try:
            # Extract photo URLs
            photos = []
            for photo in animal.get("photos", []):
                photos.append({
                    "url": photo.get("full", photo.get("large", photo.get("medium"))),
                    "small": photo.get("small"),
                    "medium": photo.get("medium"),
                    "large": photo.get("large"),
                    "full": photo.get("full"),
                })

            # Extract shelter information
            org = animal.get("organization_id", "")
            contact = animal.get("contact", {})
            address = contact.get("address", {})

            shelter = {
                "organization_id": org,
                "name": animal.get("organization_name", "Unknown Shelter"),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "address": address.get("address1"),
                "city": address.get("city", "Unknown"),
                "state": address.get("state", "XX"),
                "zip_code": address.get("postcode", "00000"),
            }

            # Extract attributes
            attributes = {
                "good_with_children": animal.get("environment", {}).get("children"),
                "good_with_dogs": animal.get("environment", {}).get("dogs"),
                "good_with_cats": animal.get("environment", {}).get("cats"),
                "house_trained": animal.get("attributes", {}).get("house_trained", False),
                "declawed": animal.get("attributes", {}).get("declawed", False),
                "spayed_neutered": animal.get("attributes", {}).get("spayed_neutered", False),
                "special_needs": animal.get("attributes", {}).get("special_needs", False),
                "shots_current": animal.get("attributes", {}).get("shots_current", True),
            }

            # Build pet data
            pet_data = {
                "pet_id": f"pf_{animal['id']}",
                "external_id": str(animal["id"]),
                "name": animal.get("name", "Unknown"),
                "species": animal.get("type", "dog").lower(),
                "breed": animal.get("breeds", {}).get("primary"),
                "mixed_breed": animal.get("breeds", {}).get("mixed", False),
                "secondary_breed": animal.get("breeds", {}).get("secondary"),
                "age": animal.get("age", "adult").lower(),
                "size": animal.get("size", "medium").lower(),
                "gender": animal.get("gender", "unknown").lower(),
                "color": animal.get("colors", {}).get("primary"),
                "coat": animal.get("coat"),
                "attributes": attributes,
                "description": animal.get("description", ""),
                "photos": photos,
                "primary_photo_url": photos[0]["url"] if photos else None,
                "shelter": shelter,
                "status": animal.get("status", "adoptable").lower(),
                "published_at": animal.get("published_at"),
            }

            pets.append(pet_data)

        except Exception as e:
            logger.warning(f"Error parsing pet data: {e}")
            continue

    return pets


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_relative_time(dt: datetime) -> str:
    """Get relative time string (e.g., '2 hours ago')."""
    now = datetime.utcnow()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(diff.days / 365)
        return f"{years} year{'s' if years != 1 else ''} ago"
