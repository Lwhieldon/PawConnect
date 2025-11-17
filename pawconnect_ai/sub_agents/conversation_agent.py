"""
Conversation Agent - User Interaction Manager
Manages natural language dialogue and user interactions.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from ..schemas.user_profile import UserProfile, UserPreferences


class ConversationAgent:
    """
    Specialized agent for managing conversations and extracting user preferences.
    """

    def __init__(self):
        """Initialize the conversation agent."""
        self.conversation_history = {}

    def process_user_input(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user input and extract intent and entities.

        Args:
            user_id: User identifier
            message: User message
            context: Optional conversation context

        Returns:
            Dictionary with intent, entities, and response
        """
        try:
            # Store conversation history
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            self.conversation_history[user_id].append({
                "role": "user",
                "message": message
            })

            # Simple intent detection (in production, would use Dialogflow CX)
            intent = self._detect_intent(message)

            # Extract entities
            entities = self._extract_entities(message, intent)

            # Generate response
            response = self._generate_response(intent, entities, context)

            # Store response in history
            self.conversation_history[user_id].append({
                "role": "assistant",
                "message": response
            })

            return {
                "intent": intent,
                "entities": entities,
                "response": response,
                "confidence": 0.85
            }

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return {
                "intent": "unknown",
                "entities": {},
                "response": "I'm sorry, I didn't understand that. Could you please rephrase?",
                "confidence": 0.0
            }

    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message."""
        message_lower = message.lower()

        # Intent patterns
        if any(word in message_lower for word in ["search", "find", "look for", "looking for"]):
            return "search_pets"
        elif any(word in message_lower for word in ["adopt", "adoption", "get a pet"]):
            return "adopt_pet"
        elif any(word in message_lower for word in ["foster", "fostering", "temporary"]):
            return "foster_pet"
        elif any(word in message_lower for word in ["recommend", "suggest", "best match"]):
            return "get_recommendations"
        elif any(word in message_lower for word in ["visit", "meet", "schedule", "appointment"]):
            return "schedule_visit"
        elif any(word in message_lower for word in ["apply", "application", "adopt this"]):
            return "submit_application"
        elif any(word in message_lower for word in ["breed", "what is", "tell me about"]):
            return "breed_info"
        elif any(word in message_lower for word in ["care", "need", "require", "requirements"]):
            return "care_info"
        elif any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "greeting"
        elif any(word in message_lower for word in ["help", "assist", "support"]):
            return "help"
        else:
            return "general_query"

    def _extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        """Extract entities from message based on intent."""
        entities = {}
        message_lower = message.lower()

        # Extract pet type
        if "dog" in message_lower:
            entities["pet_type"] = "dog"
        elif "cat" in message_lower:
            entities["pet_type"] = "cat"
        elif "rabbit" in message_lower:
            entities["pet_type"] = "rabbit"

        # Extract size
        if "small" in message_lower:
            entities["size"] = "small"
        elif "medium" in message_lower:
            entities["size"] = "medium"
        elif "large" in message_lower:
            entities["size"] = "large"

        # Extract age
        if any(word in message_lower for word in ["puppy", "kitten", "baby"]):
            entities["age"] = "baby"
        elif "young" in message_lower:
            entities["age"] = "young"
        elif "senior" in message_lower:
            entities["age"] = "senior"

        return entities

    def _generate_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate appropriate response based on intent and entities."""
        responses = {
            "greeting": "Hello! I'm here to help you find the perfect pet. What kind of pet are you looking for?",
            "search_pets": self._build_search_response(entities),
            "adopt_pet": "That's wonderful! I can help you find a pet to adopt. What are you looking for?",
            "foster_pet": "Fostering is a great way to help pets! What type of pet would you like to foster?",
            "get_recommendations": "I'd be happy to recommend some pets for you! Let me learn more about your preferences first.",
            "schedule_visit": "I can help you schedule a visit. Which pet would you like to meet?",
            "submit_application": "Great! Let's start your adoption application.",
            "breed_info": "I can provide information about different breeds. Which breed are you interested in?",
            "care_info": "I can help with pet care information. What would you like to know about?",
            "help": "I can help you:\n- Search for adoptable pets\n- Get personalized recommendations\n- Schedule shelter visits\n- Submit adoption applications\n- Answer questions about breeds and pet care\n\nWhat would you like to do?",
            "general_query": "I'm here to help you find and adopt the perfect pet. Could you tell me more about what you're looking for?"
        }

        return responses.get(intent, responses["general_query"])

    def _build_search_response(self, entities: Dict[str, Any]) -> str:
        """Build response for search intent."""
        parts = ["Great! I'll help you search for"]

        if "pet_type" in entities:
            parts.append(f"a {entities['pet_type']}")
        else:
            parts.append("pets")

        if "size" in entities:
            parts.append(f"that's {entities['size']}-sized")

        if "age" in entities:
            parts.append(f"in the {entities['age']} age range")

        return " ".join(parts) + ". What's your location?"

    def extract_user_preferences(
        self,
        conversation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract user preferences from conversation data.

        Args:
            conversation_data: Conversation context and responses

        Returns:
            Dictionary of extracted preferences
        """
        preferences = {
            "pet_type": conversation_data.get("pet_type"),
            "pet_size": conversation_data.get("size"),
            "pet_age": conversation_data.get("age"),
            "has_children": conversation_data.get("has_children", False),
            "has_other_pets": conversation_data.get("has_other_pets", False),
            "home_type": conversation_data.get("home_type", "house"),
            "has_yard": conversation_data.get("has_yard", False),
            "experience_level": conversation_data.get("experience_level", "some_experience"),
            "activity_level": conversation_data.get("activity_level", "moderate"),
        }

        return {k: v for k, v in preferences.items() if v is not None}

    def get_conversation_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a user."""
        return self.conversation_history.get(user_id, [])

    def clear_conversation_history(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
