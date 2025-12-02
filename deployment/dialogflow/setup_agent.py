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

        # Update START_PAGE with welcome message
        start_page_name = f"{flow_name}/pages/START_PAGE"
        start_page = self.pages_client.get_page(name=start_page_name)

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

        # Get intents
        intent_search_pets = self._intents_cache.get("intent.search_pets")
        intent_get_recommendations = self._intents_cache.get("intent.get_recommendations")

        if not intent_search_pets or not intent_get_recommendations:
            logger.warning("  Intents not found in cache, skipping route configuration")
            return

        # Create/update pages
        pages_list = list(self.pages_client.list_pages(parent=flow_name))
        pages_by_name = {p.display_name: p for p in pages_list}

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
                            ),
                            target_flow=flow_name
                        )
                    ]
                )
            )
            logger.info("  ✓ Pet Search page created")
        else:
            logger.info("  ✓ Pet Search page exists")

        # Get Recommendations page
        if "Get Recommendations" not in pages_by_name:
            logger.info("  Creating Get Recommendations page...")

            # Get housing_type entity
            housing_entity = self._entity_types_cache.get("housing_type")
            housing_entity_path = housing_entity.name if housing_entity else "projects/-/locations/-/agents/-/entityTypes/sys.any"

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
                            ),
                            target_flow=flow_name
                        )
                    ]
                )
            )
            logger.info("  ✓ Get Recommendations page created")
        else:
            logger.info("  ✓ Get Recommendations page exists")

        # Add transition routes to START_PAGE
        logger.info("  Configuring START_PAGE transition routes...")
        start_page = self.pages_client.get_page(name=start_page_name)

        # Get page references
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

    parser = argparse.ArgumentParser(
        description="Complete PawConnect Dialogflow CX agent setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID"
    )
    parser.add_argument(
        "--agent-id",
        help="Dialogflow CX agent ID (auto-detected if not provided)"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Agent location (default: us-central1)"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL (e.g., https://your-webhook-url/webhook)"
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
    logger.info("║  PawConnect Dialogflow CX Setup       ║")
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
        logger.info("║  ✓ Setup Complete!                    ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        logger.info("Your agent is ready! Test in Dialogflow CX Simulator:")
        logger.info("  1. 'I want to adopt a dog in Seattle'")
        logger.info("  2. 'Yes please show me recommendations'")
        logger.info("  3. 'apartment' (when asked about housing)")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("╔════════════════════════════════════════╗")
        logger.error("║  ✗ Setup Failed                       ║")
        logger.error("╚════════════════════════════════════════╝")
        sys.exit(1)


if __name__ == "__main__":
    main()
