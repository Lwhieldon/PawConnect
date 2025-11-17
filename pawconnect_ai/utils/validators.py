"""
Input validation and sanitization utilities.
"""

import re
from typing import Any, Dict, Optional
from pydantic import ValidationError
from loguru import logger

from ..schemas.user_profile import UserProfile, UserPreferences
from ..schemas.pet_data import Pet


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    # Truncate to max length
    value = value[:max_length]

    # Strip leading/trailing whitespace
    value = value.strip()

    return value


def validate_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email address

    Returns:
        True if valid email format
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number

    Returns:
        True if valid phone format
    """
    # Remove common formatting characters
    cleaned = re.sub(r"[^\d+]", "", phone)

    # Check if it's a reasonable length
    return 10 <= len(cleaned) <= 15


def validate_zip_code(zip_code: str) -> bool:
    """
    Validate US ZIP code format.

    Args:
        zip_code: ZIP code

    Returns:
        True if valid ZIP code format
    """
    # Support both 5-digit and ZIP+4 formats
    pattern = r"^\d{5}(-\d{4})?$"
    return bool(re.match(pattern, zip_code))


def validate_state_code(state: str) -> bool:
    """
    Validate US state code.

    Args:
        state: Two-letter state code

    Returns:
        True if valid state code
    """
    valid_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC", "PR", "VI", "GU", "AS", "MP"
    }
    return state.upper() in valid_states


def validate_user_input(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[UserProfile]]:
    """
    Validate user input data.

    Args:
        data: User profile data dictionary

    Returns:
        Tuple of (is_valid, error_message, user_profile)
    """
    try:
        # Sanitize string fields
        if "first_name" in data:
            data["first_name"] = sanitize_string(data["first_name"], 50)
        if "last_name" in data:
            data["last_name"] = sanitize_string(data["last_name"], 50)
        if "city" in data:
            data["city"] = sanitize_string(data["city"], 100)
        if "address" in data:
            data["address"] = sanitize_string(data["address"], 200)

        # Validate email
        if "email" in data and not validate_email(data["email"]):
            return False, "Invalid email format", None

        # Validate phone if provided
        if "phone" in data and data["phone"] and not validate_phone(data["phone"]):
            return False, "Invalid phone number format", None

        # Validate ZIP code
        if "zip_code" in data and not validate_zip_code(data["zip_code"]):
            return False, "Invalid ZIP code format", None

        # Validate state code
        if "state" in data and not validate_state_code(data["state"]):
            return False, "Invalid state code", None

        # Create and validate UserProfile
        user_profile = UserProfile(**data)
        return True, None, user_profile

    except ValidationError as e:
        logger.warning(f"User input validation failed: {e}")
        return False, str(e), None
    except Exception as e:
        logger.error(f"Unexpected error validating user input: {e}")
        return False, f"Validation error: {str(e)}", None


def validate_pet_data(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[Pet]]:
    """
    Validate pet data.

    Args:
        data: Pet data dictionary

    Returns:
        Tuple of (is_valid, error_message, pet)
    """
    try:
        # Sanitize string fields
        if "name" in data:
            data["name"] = sanitize_string(data["name"], 100)
        if "description" in data:
            data["description"] = sanitize_string(data["description"], 5000)
        if "story" in data:
            data["story"] = sanitize_string(data["story"], 5000)

        # Create and validate Pet
        pet = Pet(**data)
        return True, None, pet

    except ValidationError as e:
        logger.warning(f"Pet data validation failed: {e}")
        return False, str(e), None
    except Exception as e:
        logger.error(f"Unexpected error validating pet data: {e}")
        return False, f"Validation error: {str(e)}", None


def validate_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> bool:
    """
    Validate a score is within expected range.

    Args:
        score: Score value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if score is valid
    """
    return isinstance(score, (int, float)) and min_val <= score <= max_val


def check_pii_exposure(data: Dict[str, Any], fields_to_check: list[str]) -> list[str]:
    """
    Check for potential PII exposure in data.

    Args:
        data: Data dictionary to check
        fields_to_check: List of field names that might contain PII

    Returns:
        List of PII field names found in data
    """
    pii_fields = []
    sensitive_keys = {
        "ssn", "social_security", "password", "credit_card",
        "bank_account", "routing_number", "license", "passport"
    }

    for key in data.keys():
        key_lower = key.lower()
        if key_lower in sensitive_keys or any(
            sensitive in key_lower for sensitive in sensitive_keys
        ):
            pii_fields.append(key)

    return pii_fields


def validate_search_params(
    pet_type: Optional[str] = None,
    location: Optional[str] = None,
    distance: Optional[int] = None,
    limit: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate search parameters.

    Args:
        pet_type: Type of pet to search for
        location: Location string
        distance: Search radius in miles
        limit: Maximum number of results

    Returns:
        Tuple of (is_valid, error_message)
    """
    if pet_type:
        valid_types = ["dog", "cat", "rabbit", "bird", "small_furry", "scales_fins_other"]
        if pet_type.lower() not in valid_types:
            return False, f"Invalid pet type. Must be one of: {', '.join(valid_types)}"

    if distance is not None:
        if not isinstance(distance, int) or distance < 1 or distance > 500:
            return False, "Distance must be between 1 and 500 miles"

    if limit is not None:
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return False, "Limit must be between 1 and 100"

    if location:
        location = sanitize_string(location, 100)
        # Basic validation - should be ZIP code or "City, State"
        if not (validate_zip_code(location) or "," in location):
            return False, "Location must be a ZIP code or 'City, State' format"

    return True, None
