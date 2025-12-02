#!/usr/bin/env python3
"""
PawConnect Dialogflow CX Agent Setup
====================================

This script is the ONLY script you need to set up or update your Dialogflow CX agent.

It handles:
- Auto-detection of agent ID (or manual specification)
- Entity types (pet_species, pet_size, pet_age_group, housing_type)
- Intents with parameter annotations (search_pets, get_recommendations, etc.)
- Pages and flows with proper transition routes
- Webhook configuration
- Welcome message

Can be run multiple times safely - it updates existing resources.

Usage:
    # Auto-detect agent (recommended)
    python deployment/dialogflow/setup_agent.py --project-id YOUR_PROJECT_ID

    # Specify agent ID manually
    python deployment/dialogflow/setup_agent.py \\
        --project-id YOUR_PROJECT_ID \\
        --agent-id YOUR_AGENT_ID

    # Include webhook URL
    python deployment/dialogflow/setup_agent.py \\
        --project-id YOUR_PROJECT_ID \\
        --webhook-url https://your-webhook-url/webhook
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict
from google.cloud.dialogflowcx_v3 import (
    AgentsClient,
    IntentsClient,
    EntityTypesClient,
    PagesClient,
    FlowsClient,
    WebhooksClient
)
from google.cloud.dialogflowcx_v3.types import (
    Intent,
    EntityType,
    Page,
    Flow,
    Fulfillment,
    ResponseMessage,
    TransitionRoute,
    EventHandler,
    Webhook
)
from google.api_core.client_options import ClientOptions
from google.protobuf import field_mask_pb2
from loguru import logger

# Try to load .env file
try:
    from dotenv import load_dotenv
    # Look for .env in project root (2 levels up from this script)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass


class DialogflowSetup:
    """Complete Dialogflow CX agent setup."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        location: str = "us-central1",
        webhook_url: Optional[str] = None
    ):
        self.project_id = project_id
        self.agent_id = agent_id
        self.location = location
        self.webhook_url = webhook_url

        # Build paths
        self.agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"
        self.api_endpoint = f"{location}-dialogflow.googleapis.com"
        self.client_options = ClientOptions(api_endpoint=self.api_endpoint)

        # Initialize clients
        self.agents_client = AgentsClient(client_options=self.client_options)
        self.intents_client = IntentsClient(client_options=self.client_options)
        self.entity_types_client = EntityTypesClient(client_options=self.client_options)
        self.pages_client = PagesClient(client_options=self.client_options)
        self.flows_client = FlowsClient(client_options=self.client_options)
        self.webhooks_client = WebhooksClient(client_options=self.client_options)

        # Cache for lookups
        self._entity_types_cache = {}
        self._intents_cache = {}

    def get_or_create_entity_type(self, display_name: str, entities: List[Dict]) -> EntityType:
        """Get existing entity type or create new one."""
        if display_name in self._entity_types_cache:
            return self._entity_types_cache[display_name]

        # Try to find existing
        entity_types_list = list(self.entity_types_client.list_entity_types(parent=self.agent_path))
        for entity_type in entity_types_list:
            if entity_type.display_name == display_name:
                logger.info(f"  Found existing entity type: {display_name}")

                # Update it with new entities
                entity_type.entities.clear()
                entity_type.entities.extend([
                    EntityType.Entity(value=e["value"], synonyms=e["synonyms"])
                    for e in entities
                ])
                entity_type.enable_fuzzy_extraction = True

                updated = self.entity_types_client.update_entity_type(entity_type=entity_type)
                logger.info(f"  ✓ Updated entity type with {len(entities)} entities")
                self._entity_types_cache[display_name] = updated
                return updated

        # Create new
        logger.info(f"  Creating new entity type: {display_name}")
        entity_type = EntityType(
            display_name=display_name,
            kind=EntityType.Kind.KIND_MAP,
            entities=[
                EntityType.Entity(value=e["value"], synonyms=e["synonyms"])
                for e in entities
            ],
            enable_fuzzy_extraction=True
        )

        created = self.entity_types_client.create_entity_type(
            parent=self.agent_path,
            entity_type=entity_type
        )
        logger.info(f"  ✓ Created entity type with {len(entities)} entities")
        self._entity_types_cache[display_name] = created
        return created

    def get_or_create_intent(
        self,
        display_name: str,
        training_phrases: List[List[Dict]],
        parameters: Optional[List[Dict]] = None
    ) -> Intent:
        """Get existing intent or create new one."""
        if display_name in self._intents_cache:
            return self._intents_cache[display_name]

        # Try to find existing
        intents_list = list(self.intents_client.list_intents(parent=self.agent_path))
        for intent in intents_list:
            if intent.display_name == display_name:
                logger.info(f"  Found existing intent: {display_name}")

                # Update training phrases
                intent.training_phrases.clear()
                intent.training_phrases.extend([
                    Intent.TrainingPhrase(
                        parts=[
                            Intent.TrainingPhrase.Part(
                                text=part["text"],
                                parameter_id=part.get("parameter_id")
                            )
                            for part in phrase
                        ],
                        repeat_count=1
                    )
                    for phrase in training_phrases
                ])

                # Update parameters if provided
                if parameters:
                    intent.parameters.clear()
                    intent.parameters.extend([
                        Intent.Parameter(
                            id=param["id"],
                            entity_type=param["entity_type"]
                        )
                        for param in parameters
                    ])

                updated = self.intents_client.update_intent(intent=intent)
                logger.info(f"  ✓ Updated intent with {len(training_phrases)} training phrases")
                self._intents_cache[display_name] = updated
                return updated

        # Create new
        logger.info(f"  Creating new intent: {display_name}")
        intent = Intent(
            display_name=display_name,
            training_phrases=[
                Intent.TrainingPhrase(
                    parts=[
                        Intent.TrainingPhrase.Part(
                            text=part["text"],
                            parameter_id=part.get("parameter_id")
                        )
                        for part in phrase
                    ],
                    repeat_count=1
                )
                for phrase in training_phrases
            ],
            parameters=[
                Intent.Parameter(
                    id=param["id"],
                    entity_type=param["entity_type"]
                )
                for param in parameters
            ] if parameters else [],
            priority=500000
        )

        created = self.intents_client.create_intent(
            parent=self.agent_path,
            intent=intent
        )
        logger.info(f"  ✓ Created intent with {len(training_phrases)} training phrases")
        self._intents_cache[display_name] = created
        return created

    def setup_entity_types(self):
        """Create/update all entity types."""
        logger.info("Setting up entity types...")

        # Housing type
        self.get_or_create_entity_type(
            "housing_type",
            [
                {"value": "apartment", "synonyms": ["apartment", "apt", "flat", "apartments", "apartment building"]},
                {"value": "house", "synonyms": ["house", "home", "single family", "single-family home"]},
                {"value": "condo", "synonyms": ["condo", "condominium", "townhouse", "townhome"]},
                {"value": "own", "synonyms": ["own", "owner", "homeowner", "I own", "own my home"]},
                {"value": "rent", "synonyms": ["rent", "renter", "renting", "lease", "I rent", "renting a place"]},
                {"value": "live_with_family", "synonyms": ["live with family", "parents", "family home", "with parents", "parents house"]}
            ]
        )

        # Pet species
        self.get_or_create_entity_type(
            "pet_species",
            [
                {"value": "dog", "synonyms": ["dog", "dogs", "puppy", "puppies", "canine"]},
                {"value": "cat", "synonyms": ["cat", "cats", "kitten", "kittens", "feline"]},
                {"value": "rabbit", "synonyms": ["rabbit", "rabbits", "bunny", "bunnies"]},
                {"value": "bird", "synonyms": ["bird", "birds", "parrot", "parakeet"]},
                {"value": "small_animal", "synonyms": ["hamster", "guinea pig", "ferret"]}
            ]
        )

        # Pet size
        self.get_or_create_entity_type(
            "pet_size",
            [
                {"value": "small", "synonyms": ["small", "tiny", "little", "miniature"]},
                {"value": "medium", "synonyms": ["medium", "average", "mid-sized"]},
                {"value": "large", "synonyms": ["large", "big", "giant", "huge"]},
                {"value": "extra_large", "synonyms": ["extra-large", "xl", "giant", "huge", "very large"]}
            ]
        )

        # Pet age group
        self.get_or_create_entity_type(
            "pet_age_group",
            [
                {"value": "baby", "synonyms": ["baby", "newborn", "infant"]},
                {"value": "young", "synonyms": ["young", "puppy", "kitten", "juvenile"]},
                {"value": "adult", "synonyms": ["adult", "mature", "grown"]},
                {"value": "senior", "synonyms": ["senior", "elderly", "old", "older"]}
            ]
        )

        logger.info("✓ Entity types configured")

    def setup_intents(self):
        """Create/update all intents."""
        logger.info("Setting up intents...")

        # Get system entity type path
        sys_any = "projects/-/locations/-/agents/-/entityTypes/sys.any"

        # intent.search_pets with parameter annotations
        self.get_or_create_intent(
            "intent.search_pets",
            [
                [{"text": "I want to adopt a "}, {"text": "dog", "parameter_id": "species"}, {"text": " in "}, {"text": "Seattle", "parameter_id": "location"}],
                [{"text": "Show me "}, {"text": "cats", "parameter_id": "species"}, {"text": " in "}, {"text": "Portland", "parameter_id": "location"}],
                [{"text": "I'm looking for a "}, {"text": "puppy", "parameter_id": "species"}],
                [{"text": "Search for pets in "}, {"text": "Boston", "parameter_id": "location"}],
                [{"text": "Find me a "}, {"text": "kitten", "parameter_id": "species"}],
                [{"text": "I want to search for a pet"}],
                [{"text": "Can you help me find a pet"}]
            ],
            parameters=[
                {"id": "location", "entity_type": sys_any},
                {"id": "species", "entity_type": sys_any},
                {"id": "breed", "entity_type": sys_any}
            ]
        )

        # intent.get_recommendations with affirmative responses
        self.get_or_create_intent(
            "intent.get_recommendations",
            [
                [{"text": "Yes"}],
                [{"text": "Yes please"}],
                [{"text": "Show me recommendations"}],
                [{"text": "Yes please show me recommendations"}],
                [{"text": "Sure"}],
                [{"text": "Yes I'd like recommendations"}],
                [{"text": "That would be great"}],
                [{"text": "What pet would be good for me"}],
                [{"text": "Can you recommend a pet"}],
                [{"text": "Which pet should I adopt"}],
                [{"text": "Help me find the right pet"}],
                [{"text": "I don't know what pet to get"}],
                [{"text": "Recommend a pet for my lifestyle"}],
                [{"text": "Give me recommendations"}],
                [{"text": "I need help choosing a pet"}]
            ]
        )

        # Other intents
        self.get_or_create_intent(
            "intent.schedule_visit",
            [
                [{"text": "I want to schedule a visit"}],
                [{"text": "Can I meet the pet"}],
                [{"text": "Schedule a time to see the pet"}],
                [{"text": "I'd like to visit the shelter"}],
                [{"text": "Book a visit"}],
                [{"text": "Set up an appointment"}]
            ]
        )

        self.get_or_create_intent(
            "intent.adoption_application",
            [
                [{"text": "I want to adopt"}],
                [{"text": "Start adoption application"}],
                [{"text": "Apply to adopt this pet"}],
                [{"text": "I'd like to adopt"}],
                [{"text": "Begin adoption process"}],
                [{"text": "Submit adoption application"}]
            ]
        )

        self.get_or_create_intent(
            "intent.foster_application",
            [
                [{"text": "I want to foster"}],
                [{"text": "Start foster application"}],
                [{"text": "Apply to foster this pet"}],
                [{"text": "I'd like to foster"}],
                [{"text": "Can I foster temporarily"}]
            ]
        )

        self.get_or_create_intent(
            "intent.search_more",
            [
                [{"text": "Show me more pets"}],
                [{"text": "Search again"}],
                [{"text": "Find other pets"}],
                [{"text": "Look for different pets"}],
                [{"text": "Start a new search"}]
            ]
        )

        self.get_or_create_intent(
            "intent.ask_question",
            [
                [{"text": "Tell me about Golden Retrievers"}],
                [{"text": "What do I need to know about cats"}],
                [{"text": "How much exercise does a dog need"}],
                [{"text": "What should I prepare before adopting"}],
                [{"text": "What's the adoption process"}]
            ]
        )

        logger.info("✓ Intents configured")

    def setup_webhook(self) -> Optional[str]:
        """Create/update webhook if URL provided."""
        if not self.webhook_url:
            logger.info("No webhook URL provided, skipping webhook setup")
            return None

        logger.info(f"Setting up webhook: {self.webhook_url}")

        # Try to find existing webhook
        webhooks_list = list(self.webhooks_client.list_webhooks(parent=self.agent_path))
        for webhook in webhooks_list:
            if webhook.display_name == "PawConnect Webhook":
                logger.info("  Found existing webhook, updating...")
                webhook.generic_web_service.uri = self.webhook_url
                updated = self.webhooks_client.update_webhook(webhook=webhook)
                logger.info("  ✓ Webhook updated")
                return updated.name

        # Create new
        logger.info("  Creating new webhook...")
        webhook = Webhook(
            display_name="PawConnect Webhook",
            generic_web_service=Webhook.GenericWebService(uri=self.webhook_url),
            timeout=field_mask_pb2.Duration(seconds=30)
        )
        created = self.webhooks_client.create_webhook(
            parent=self.agent_path,
            webhook=webhook
        )
        logger.info("  ✓ Webhook created")
        return created.name

    def setup_flows_and_pages(self, webhook_name: Optional[str] = None):
        """Set up flows, pages, and transition routes."""
        logger.info("Setting up flows and pages...")

        # Get default flow
        flows_list = list(self.flows_client.list_flows(parent=self.agent_path))
        default_flow = next((f for f in flows_list if f.display_name == "Default Start Flow"), None)

        if not default_flow:
            logger.error("Default Start Flow not found")
            return

        flow_name = default_flow.name
        logger.info(f"  Using flow: {flow_name}")

        # Get intents first (needed for routes)
        intent_search_pets = self._intents_cache.get("intent.search_pets")
        intent_get_recommendations = self._intents_cache.get("intent.get_recommendations")

        if not intent_search_pets or not intent_get_recommendations:
            logger.warning("  Intents not found in cache, skipping page configuration")
            return

        # List all pages in the flow
        pages_list = list(self.pages_client.list_pages(parent=flow_name))
        pages_by_name = {p.display_name: p for p in pages_list}

        # Debug: Log all page names
        logger.info(f"  Found {len(pages_list)} pages: {[p.display_name for p in pages_list]}")

        # Find START_PAGE - try different possible names
        start_page = None
        for page in pages_list:
            if page.display_name in ["START_PAGE", "Start Page", "start_page"]:
                start_page = page
                logger.info(f"  Found START_PAGE: {page.name}")
                break

        # If not found in list, try to access START_PAGE directly with special ID
        if not start_page:
            try:
                # START_PAGE has a special UUID of all zeros
                start_page_path = f"{flow_name}/pages/00000000-0000-0000-0000-000000000000"
                logger.info(f"  Attempting to access START_PAGE directly: {start_page_path}")
                start_page = self.pages_client.get_page(name=start_page_path)
                logger.info("  ✓ Successfully accessed START_PAGE directly!")
            except Exception as e:
                logger.info(f"  Could not access START_PAGE directly: {e}")
                start_page = None

        # CRITICAL FIX: Update the problematic sys.no-match-default event handler at flow level
        # Instead of deleting (which API won't allow), we'll update it with a better message
        try:
            flow = self.flows_client.get_flow(name=flow_name)

            # Find and update sys.no-match-default handlers that have the welcome message
            updated = False
            for eh in flow.event_handlers:
                if eh.event == "sys.no-match-default":
                    # Check if this handler has the welcome message
                    has_welcome = any(
                        "Welcome to PawConnect" in text
                        for msg in eh.trigger_fulfillment.messages
                        for text in (msg.text.text if hasattr(msg, 'text') else [])
                    )

                    if has_welcome:
                        # Update with a more appropriate message for no-match scenarios
                        eh.trigger_fulfillment.messages[:] = [
                            ResponseMessage(
                                text=ResponseMessage.Text(
                                    text=["I didn't quite catch that. Could you rephrase or try again?"]
                                )
                            )
                        ]
                        updated = True
                        logger.info("  ✓ Updated sys.no-match-default event handler with appropriate message")

            if updated:
                # Update the flow
                update_mask = {"paths": ["event_handlers"]}
                self.flows_client.update_flow(flow=flow, update_mask=update_mask)
            else:
                logger.info("  No problematic event handlers found to update")
        except Exception as e:
            logger.warning(f"  Could not update flow event handlers: {e}")

        # Configure START_PAGE if we found it
        if not start_page:
            logger.info("  START_PAGE not accessible, will configure routes at flow level...")
            # We'll skip the welcome message configuration and just set up routes at flow level
            # The welcome message can be configured manually in the Dialogflow Console if needed
        else:
            # Update START_PAGE with welcome message
            logger.info("  Configuring welcome message on START_PAGE...")
            welcome_message = (
                "Welcome to PawConnect! I'm here to help you find your perfect pet companion. "
                "I can help you search for pets, learn about specific animals, schedule visits, "
                "or start an adoption application. What would you like to do?"
            )

            start_page.entry_fulfillment = Fulfillment(
                messages=[
                    ResponseMessage(
                        text=ResponseMessage.Text(text=[welcome_message])
                    )
                ]
            )

            self.pages_client.update_page(page=start_page)
            logger.info("  ✓ Welcome message configured")

        # Pet Search page
        if "Pet Search" not in pages_by_name:
            logger.info("  Creating Pet Search page...")
            pet_search_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Pet Search",
                    form=Page.Form(
                        parameters=[
                            Page.Form.Parameter(
                                display_name="location",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                                required=True,
                                fill_behavior=Page.Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Where are you located?"]))]
                                    )
                                )
                            ),
                            Page.Form.Parameter(
                                display_name="species",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                                required=True,
                                fill_behavior=Page.Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["What type of pet are you looking for?"]))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="search-pets"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Searching for pets..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Pet Search page created")
        else:
            # Update existing page to ensure webhook route is configured
            logger.info("  Updating Pet Search page with webhook route...")
            pet_search_page = pages_by_name["Pet Search"]

            # Clear entry_fulfillment to prevent double webhook calls
            # The webhook should ONLY be called when form is complete, not when entering the page
            pet_search_page.entry_fulfillment = Fulfillment()

            # Clear all page-level event handlers to prevent interference
            event_handler_count = len(pet_search_page.event_handlers)
            pet_search_page.event_handlers.clear()
            if event_handler_count > 0:
                logger.info(f"  Cleared {event_handler_count} page-level event handler(s) from Pet Search")

            # Update transition routes to ensure webhook is called when form is complete
            pet_search_page.transition_routes.clear()
            pet_search_page.transition_routes.append(
                TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="search-pets"
                    ) if webhook_name else Fulfillment(
                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Searching for pets..."]))]
                    )
                    # No target specified - let webhook response control the flow
                )
            )

            # Update the page
            self.pages_client.update_page(page=pet_search_page)
            logger.info("  ✓ Pet Search page updated (cleared entry fulfillment, set webhook route)")

        # Get Recommendations page
        # Get housing_type entity
        housing_entity = self._entity_types_cache.get("housing_type")
        housing_entity_path = housing_entity.name if housing_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

        logger.info(f"  Using housing_type entity: {housing_entity_path}")

        if "Get Recommendations" not in pages_by_name:
            logger.info("  Creating Get Recommendations page...")

            get_rec_page = self.pages_client.create_page(
                parent=flow_name,
                page=Page(
                    display_name="Get Recommendations",
                    form=Page.Form(
                        parameters=[
                            Page.Form.Parameter(
                                display_name="housing",
                                entity_type=housing_entity_path,
                                required=True,
                                fill_behavior=Page.Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["What type of housing do you have? (apartment, house, condo, etc.)"]))]
                                    )
                                )
                            ),
                            Page.Form.Parameter(
                                display_name="experience",
                                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any",
                                required=True,
                                fill_behavior=Page.Form.Parameter.FillBehavior(
                                    initial_prompt_fulfillment=Fulfillment(
                                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Do you have experience with pets?"]))]
                                    )
                                )
                            )
                        ]
                    ),
                    transition_routes=[
                        TransitionRoute(
                            condition="$page.params.status = \"FINAL\"",
                            trigger_fulfillment=Fulfillment(
                                webhook=webhook_name,
                                tag="get-recommendations"
                            ) if webhook_name else Fulfillment(
                                messages=[ResponseMessage(text=ResponseMessage.Text(text=["Getting recommendations..."]))]
                            )
                            # No target specified - let webhook response control the flow
                        )
                    ]
                )
            )
            logger.info("  ✓ Get Recommendations page created")
        else:
            # Update existing page to ensure correct entity type and transition routes
            logger.info("  Updating Get Recommendations page with correct entity type...")
            get_rec_page = pages_by_name["Get Recommendations"]

            # Update the form parameters with correct entity types and prompts
            # Configure housing parameter
            housing_param = get_rec_page.form.parameters[0]
            housing_param.entity_type = housing_entity_path
            housing_param.display_name = "housing"
            housing_param.required = True
            # Update the fill_behavior prompt
            housing_param.fill_behavior.initial_prompt_fulfillment.messages[:] = [
                ResponseMessage(text=ResponseMessage.Text(
                    text=["What type of housing do you have? (apartment, house, condo, etc.)"]
                ))
            ]

            # Configure experience parameter if it exists
            if len(get_rec_page.form.parameters) >= 2:
                experience_param = get_rec_page.form.parameters[1]
                experience_param.entity_type = "projects/-/locations/-/agents/-/entityTypes/sys.any"
                experience_param.display_name = "experience"
                experience_param.required = True
                # Update the fill_behavior prompt
                experience_param.fill_behavior.initial_prompt_fulfillment.messages[:] = [
                    ResponseMessage(text=ResponseMessage.Text(
                        text=["Do you have experience with pets?"]
                    ))
                ]

            # Clear entry_fulfillment to prevent double webhook calls
            # The webhook should ONLY be called when form is complete, not when entering the page
            get_rec_page.entry_fulfillment = Fulfillment()

            # CRITICAL: Clear all page-level event handlers
            # These can interfere with transition routes and cause loops
            event_handler_count = len(get_rec_page.event_handlers)
            get_rec_page.event_handlers.clear()
            if event_handler_count > 0:
                logger.info(f"  Cleared {event_handler_count} page-level event handler(s)")

            # Update transition routes to ensure webhook is called when form is complete
            get_rec_page.transition_routes.clear()
            get_rec_page.transition_routes.append(
                TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="get-recommendations"
                    ) if webhook_name else Fulfillment(
                        messages=[ResponseMessage(text=ResponseMessage.Text(text=["Getting recommendations..."]))]
                    )
                    # No target specified - let webhook response control the flow
                )
            )

            # Update the page
            self.pages_client.update_page(page=get_rec_page)
            logger.info("  ✓ Get Recommendations page updated (cleared entry fulfillment, set webhook route)")

        # Add transition routes to START_PAGE
        if start_page:
            logger.info("  Configuring START_PAGE transition routes...")

            # Refresh pages list to get newly created pages
            pages_list = list(self.pages_client.list_pages(parent=flow_name))
            pet_search_page = next((p for p in pages_list if p.display_name == "Pet Search"), None)
            get_rec_page = next((p for p in pages_list if p.display_name == "Get Recommendations"), None)

            if pet_search_page and get_rec_page:
                start_page.transition_routes.clear()
                start_page.transition_routes.extend([
                    TransitionRoute(
                        intent=intent_search_pets.name,
                        target_page=pet_search_page.name,
                        trigger_fulfillment=Fulfillment(
                            set_parameter_actions=[
                                Fulfillment.SetParameterAction(
                                    parameter="location",
                                    value="$session.params.location"
                                ),
                                Fulfillment.SetParameterAction(
                                    parameter="species",
                                    value="$session.params.species"
                                )
                            ]
                        )
                    ),
                    TransitionRoute(
                        intent=intent_get_recommendations.name,
                        target_page=get_rec_page.name
                    )
                ])

                self.pages_client.update_page(page=start_page)
                logger.info("  ✓ Transition routes configured")
        else:
            # If START_PAGE not found, add routes to flow level
            logger.info("  Configuring transition routes at flow level...")

            # Refresh pages list to get newly created pages
            pages_list = list(self.pages_client.list_pages(parent=flow_name))
            pet_search_page = next((p for p in pages_list if p.display_name == "Pet Search"), None)
            get_rec_page = next((p for p in pages_list if p.display_name == "Get Recommendations"), None)

            if pet_search_page and get_rec_page:
                # Get the flow and add transition routes
                flow = self.flows_client.get_flow(name=flow_name)

                # Keep existing routes but filter out our intents first to avoid duplicates
                existing_routes = [
                    route for route in flow.transition_routes
                    if route.intent not in [intent_search_pets.name, intent_get_recommendations.name]
                ]

                # Add our routes
                new_routes = [
                    TransitionRoute(
                        intent=intent_search_pets.name,
                        target_page=pet_search_page.name,
                        trigger_fulfillment=Fulfillment(
                            set_parameter_actions=[
                                Fulfillment.SetParameterAction(
                                    parameter="location",
                                    value="$session.params.location"
                                ),
                                Fulfillment.SetParameterAction(
                                    parameter="species",
                                    value="$session.params.species"
                                )
                            ]
                        )
                    ),
                    TransitionRoute(
                        intent=intent_get_recommendations.name,
                        target_page=get_rec_page.name
                    )
                ]

                # Update flow with combined routes
                flow.transition_routes.clear()
                flow.transition_routes.extend(existing_routes + new_routes)

                self.flows_client.update_flow(flow=flow)
                logger.info("  ✓ Transition routes configured at flow level")

        logger.info("✓ Flows and pages configured")

    def run_complete_setup(self):
        """Run complete setup."""
        try:
            logger.info(f"Setting up agent: {self.agent_path}")
            logger.info("")

            self.setup_entity_types()
            logger.info("")

            self.setup_intents()
            logger.info("")

            webhook_name = self.setup_webhook()
            logger.info("")

            self.setup_flows_and_pages(webhook_name)
            logger.info("")

            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def find_agent(project_id: str, location: str = "us-central1") -> Optional[str]:
    """Find agent ID automatically."""
    try:
        parent = f"projects/{project_id}/locations/{location}"
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)
        agents_client = AgentsClient(client_options=client_options)

        agents = list(agents_client.list_agents(parent=parent))
        if agents:
            agent_id = agents[0].name.split("/")[-1]
            logger.info(f"Auto-detected agent: {agents[0].display_name} ({agent_id})")
            return agent_id
        else:
            logger.error("No agents found in project")
            return None
    except Exception as e:
        logger.error(f"Failed to find agent: {e}")
        return None


def main():
    """Main entry point."""
    import argparse

    # Get defaults from environment variables
    default_project_id = os.getenv("GCP_PROJECT_ID")
    default_agent_id = os.getenv("DIALOGFLOW_AGENT_ID")
    default_location = os.getenv("DIALOGFLOW_LOCATION", "us-central1")
    default_webhook_url = os.getenv("DIALOGFLOW_WEBHOOK_URL")

    parser = argparse.ArgumentParser(
        description="Complete PawConnect Dialogflow CX agent setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--project-id",
        default=default_project_id,
        required=not default_project_id,
        help=f"GCP project ID (default: from .env GCP_PROJECT_ID={default_project_id or 'not set'})"
    )
    parser.add_argument(
        "--agent-id",
        default=default_agent_id,
        help=f"Dialogflow CX agent ID (default: from .env DIALOGFLOW_AGENT_ID={default_agent_id or 'auto-detect'})"
    )
    parser.add_argument(
        "--location",
        default=default_location,
        help=f"Agent location (default: from .env DIALOGFLOW_LOCATION={default_location})"
    )
    parser.add_argument(
        "--webhook-url",
        default=default_webhook_url,
        help=f"Webhook URL (default: from .env DIALOGFLOW_WEBHOOK_URL={default_webhook_url or 'not set'})"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="INFO"
    )

    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  PawConnect Dialogflow CX Setup        ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")

    # Find agent if not provided
    agent_id = args.agent_id
    if not agent_id:
        logger.info("Agent ID not provided, auto-detecting...")
        agent_id = find_agent(args.project_id, args.location)
        if not agent_id:
            logger.error("Could not find agent. Please provide --agent-id")
            sys.exit(1)
        logger.info("")

    # Run setup
    setup = DialogflowSetup(
        project_id=args.project_id,
        agent_id=agent_id,
        location=args.location,
        webhook_url=args.webhook_url
    )

    success = setup.run_complete_setup()

    if success:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  ✓ Setup Complete!                     ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        logger.info("✅ What was configured:")
        logger.info("  • Entity types (housing, species, size, age)")
        logger.info("  • Intents with parameter annotations")
        logger.info("  • Pages (Pet Search, Get Recommendations)")
        logger.info("  • Transition routes at flow level")
        logger.info("  • Webhook configuration")
        logger.info("")
        logger.info("📝 Manual step (optional):")
        logger.info("  To add a welcome message, go to Dialogflow Console:")
        logger.info("  Build > Default Start Flow > Entry fulfillment")
        logger.info("  Add: 'Welcome to PawConnect! I'm here to help you")
        logger.info("        find your perfect pet companion.'")
        logger.info("")
        logger.info("🧪 Test in Dialogflow CX Simulator:")
        logger.info("  1. 'I want to adopt a dog in Seattle'")
        logger.info("  2. 'Yes please show me recommendations'")
        logger.info("  3. 'apartment' (when asked about housing)")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("╔════════════════════════════════════════╗")
        logger.error("║  ✗ Setup Failed                        ║")
        logger.error("╚════════════════════════════════════════╝")
        sys.exit(1)


if __name__ == "__main__":
    main()
