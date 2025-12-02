"""
Conversation Agent - User Interaction Manager
Manages natural language dialogue and user interactions.
Uses Google's Gemini AI for advanced natural language understanding.
"""

from typing import Dict, Any, List, Optional
import json
from loguru import logger

from ..schemas.user_profile import UserProfile, UserPreferences
from ..config import get_settings

# Lazy import for Vertex AI (allows operation without credentials in testing)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig, Part
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    logger.warning("Vertex AI SDK not available. Falling back to keyword-based conversation.")


class ConversationAgent:
    """
    Specialized agent for managing conversations and extracting user preferences.
    Uses Google Gemini AI for advanced natural language understanding.
    """

    def __init__(self):
        """Initialize the conversation agent."""
        self.conversation_history = {}
        self.settings = get_settings()
        self.gemini_model = None
        self.use_gemini = self.settings.use_gemini_for_conversation and VERTEXAI_AVAILABLE

        # Initialize Gemini if enabled and available
        if self.use_gemini:
            try:
                vertexai.init(
                    project=self.settings.gcp_project_id,
                    location=self.settings.gcp_region
                )
                self.gemini_model = GenerativeModel(self.settings.gemini_model_name)
                logger.info(f"Gemini model initialized: {self.settings.gemini_model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}. Falling back to keyword matching.")
                self.use_gemini = False

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

            # Use Gemini for NLU if available, otherwise fall back to keyword matching
            if self.use_gemini and self.gemini_model:
                try:
                    result = self._process_with_gemini(message, context, user_id)
                    intent = result["intent"]
                    entities = result["entities"]
                    response = result.get("response", self._generate_response(intent, entities, context))
                    confidence = result.get("confidence", 0.9)
                except Exception as e:
                    logger.warning(f"Gemini processing failed: {e}. Falling back to keyword matching.")
                    intent = self._detect_intent(message)
                    entities = self._extract_entities(message, intent)
                    response = self._generate_response(intent, entities, context)
                    confidence = 0.85
            else:
                # Fallback to keyword-based intent detection
                intent = self._detect_intent(message)
                entities = self._extract_entities(message, intent)
                response = self._generate_response(intent, entities, context)
                confidence = 0.85

            # Store response in history
            self.conversation_history[user_id].append({
                "role": "assistant",
                "message": response
            })

            return {
                "intent": intent,
                "entities": entities,
                "response": response,
                "confidence": confidence,
                "model": "gemini" if (self.use_gemini and self.gemini_model) else "keyword"
            }

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return {
                "intent": "unknown",
                "entities": {},
                "response": "I'm sorry, I didn't understand that. Could you please rephrase?",
                "confidence": 0.0,
                "model": "error"
            }

    def _process_with_gemini(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process user message using Gemini AI for intent detection and entity extraction.

        Args:
            message: User message to process
            context: Optional conversation context
            user_id: User identifier for conversation history

        Returns:
            Dictionary with intent, entities, and optional response
        """
        # Build conversation history for context
        history = self.get_conversation_history(user_id)
        history_text = "\n".join([
            f"{msg['role']}: {msg['message']}"
            for msg in history[-5:]  # Last 5 messages for context
        ])

        # Create prompt for Gemini with structured output
        prompt = f"""You are a helpful pet adoption assistant for PawConnect. Analyze the user's message and extract:
1. **Intent**: The user's primary goal
2. **Entities**: Specific details mentioned (pet_type, size, age, etc.)
3. **Response**: A natural, helpful response

**Available Intents (choose the most immediate action the user wants):**
- search_pets: User wants to search/browse/find/look for available pets (e.g., "I'm looking for a dog", "show me cats", "find me a pet")
- adopt_pet: User is ready to start the adoption process/application for a specific pet they've already chosen
- foster_pet: User is ready to start the fostering process/application
- get_recommendations: User wants personalized pet recommendations based on their lifestyle
- schedule_visit: User wants to schedule a visit/meeting with a specific pet
- submit_application: User wants to submit an adoption/foster application
- breed_info: User wants information about specific breeds
- care_info: User wants pet care information
- greeting: User is greeting/starting conversation
- help: User needs help/assistance
- general_query: General question or unclear intent

**Important:** If the user is looking for or searching for a pet to adopt, use "search_pets" not "adopt_pet"

**Conversation History:**
{history_text}

**Current Message:**
{message}

**Additional Context:**
{json.dumps(context) if context else "None"}

**Output Format (JSON):**
{{
  "intent": "one of the intents listed above",
  "entities": {{
    "pet_type": "dog/cat/rabbit/etc (if mentioned)",
    "size": "small/medium/large (if mentioned)",
    "age": "baby/young/adult/senior (if mentioned)",
    "breed": "specific breed (if mentioned)",
    "location": "location (if mentioned)",
    "other": "any other relevant details"
  }},
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of why this intent was chosen",
  "response": "A natural, empathetic response to the user"
}}

Respond with ONLY the JSON, no additional text."""

        # Call Gemini
        generation_config = GenerationConfig(
            temperature=self.settings.gemini_temperature,
            max_output_tokens=self.settings.gemini_max_output_tokens,
            response_mime_type="application/json"
        )

        response = self.gemini_model.generate_content(
            prompt,
            generation_config=generation_config
        )

        # Parse Gemini response
        try:
            result = json.loads(response.text)
            logger.info(f"Gemini analysis: {result.get('reasoning', 'No reasoning provided')}")
            return {
                "intent": result.get("intent", "general_query"),
                "entities": result.get("entities", {}),
                "confidence": result.get("confidence", 0.9),
                "response": result.get("response", "")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}. Response: {response.text}")
            # Fallback to keyword matching
            return {
                "intent": self._detect_intent(message),
                "entities": self._extract_entities(message, self._detect_intent(message)),
                "confidence": 0.5
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
