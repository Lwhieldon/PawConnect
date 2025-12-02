#!/usr/bin/env python3
"""
Dialogflow CX Automation Script for PawConnect
Automates creation of flows, pages, webhooks, and routes using the Python client library.
"""

import os
import sys
from typing import Dict, List, Optional
from google.cloud.dialogflowcx_v3 import (
    AgentsClient,
    FlowsClient,
    PagesClient,
    WebhooksClient,
    EntityTypesClient,
    IntentsClient,
)
from google.cloud.dialogflowcx_v3.types import (
    Agent,
    Flow,
    Page,
    Webhook,
    TransitionRoute,
    Fulfillment,
    EventHandler,
    Form,
    ResponseMessage,
)
from google.api_core import exceptions
from google.api_core.client_options import ClientOptions
from loguru import logger


class DialogflowAutomation:
    """Automates Dialogflow CX agent setup."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        location: str = "us-central1",
        webhook_url: Optional[str] = None
    ):
        """
        Initialize Dialogflow automation.

        Args:
            project_id: GCP project ID
            agent_id: Dialogflow CX agent ID
            location: Agent location (default: us-central1)
            webhook_url: Webhook URL for fulfillments
        """
        self.project_id = project_id
        self.agent_id = agent_id
        self.location = location
        self.webhook_url = webhook_url

        # Build agent path
        self.agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"

        # Build regional API endpoint
        api_endpoint = f"{self.location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        # Initialize clients with regional endpoint
        self.agents_client = AgentsClient(client_options=client_options)
        self.flows_client = FlowsClient(client_options=client_options)
        self.pages_client = PagesClient(client_options=client_options)
        self.webhooks_client = WebhooksClient(client_options=client_options)
        self.entity_types_client = EntityTypesClient(client_options=client_options)
        self.intents_client = IntentsClient(client_options=client_options)

        logger.info(f"Initialized Dialogflow automation for agent: {self.agent_path}")
        logger.info(f"Using regional endpoint: {api_endpoint}")

    def verify_agent(self) -> bool:
        """Verify that the agent exists."""
        try:
            agent = self.agents_client.get_agent(name=self.agent_path)
            logger.info(f"✓ Agent verified: {agent.display_name}")
            return True
        except exceptions.NotFound:
            logger.error(f"✗ Agent not found: {self.agent_path}")
            return False
        except Exception as e:
            logger.error(f"✗ Error verifying agent: {e}")
            return False

    def get_entity_type_name(self, display_name: str) -> Optional[str]:
        """
        Get the full resource name of an entity type by its display name.

        Args:
            display_name: Entity type display name (e.g., 'pet_species')

        Returns:
            Full resource name if found, None otherwise
        """
        try:
            entity_types_list = list(self.entity_types_client.list_entity_types(parent=self.agent_path))

            for entity_type in entity_types_list:
                if entity_type.display_name == display_name:
                    logger.info(f"  Checking '{display_name}': ✓ Found")
                    return entity_type.name

            # Not found
            entity_names = [et.display_name for et in entity_types_list]
            logger.info(f"  Checking '{display_name}': ✗ Not found")
            if entity_names:
                logger.info(f"    Available entity types: {', '.join(entity_names)}")

            return None
        except Exception as e:
            logger.warning(f"⚠ Error checking entity type '{display_name}': {e}")
            return None

    def entity_type_exists(self, entity_type_name: str) -> bool:
        """
        Check if an entity type exists in the agent.

        Args:
            entity_type_name: Entity type display name (e.g., 'pet_species')

        Returns:
            True if entity type exists, False otherwise
        """
        return self.get_entity_type_name(entity_type_name) is not None

    def get_intent_name(self, display_name: str) -> Optional[str]:
        """
        Get the full resource name of an intent by its display name.

        Args:
            display_name: Intent display name (e.g., 'intent.search_pets')

        Returns:
            Full resource name if found, None otherwise
        """
        try:
            intents_list = list(self.intents_client.list_intents(parent=self.agent_path))

            for intent in intents_list:
                if intent.display_name == display_name:
                    logger.debug(f"  Found intent '{display_name}'")
                    return intent.name

            logger.debug(f"  Intent '{display_name}' not found")
            return None
        except Exception as e:
            logger.warning(f"⚠ Error checking intent '{display_name}': {e}")
            return None

    def create_webhook(self, display_name: str, timeout_seconds: int = 30) -> Optional[str]:
        """
        Create or update a webhook.

        Args:
            display_name: Webhook display name
            timeout_seconds: Webhook timeout in seconds

        Returns:
            Webhook resource name or None if creation failed
        """
        if not self.webhook_url:
            logger.warning("⚠ No webhook URL provided, skipping webhook creation")
            return None

        try:
            # Check if webhook already exists
            webhooks = self.webhooks_client.list_webhooks(parent=self.agent_path)
            for webhook in webhooks:
                if webhook.display_name == display_name:
                    logger.info(f"⚠ Webhook '{display_name}' already exists, using existing: {webhook.name}")
                    return webhook.name

            # Create new webhook
            webhook = Webhook(
                display_name=display_name,
                generic_web_service=Webhook.GenericWebService(
                    uri=self.webhook_url
                ),
                timeout=f"{timeout_seconds}s"
            )

            created_webhook = self.webhooks_client.create_webhook(
                parent=self.agent_path,
                webhook=webhook
            )

            logger.info(f"✓ Created webhook: {display_name}")
            return created_webhook.name

        except Exception as e:
            logger.error(f"✗ Error creating webhook '{display_name}': {e}")
            return None

    def get_default_start_flow(self) -> Optional[str]:
        """Get the Default Start Flow resource name."""
        try:
            flows = self.flows_client.list_flows(parent=self.agent_path)
            for flow in flows:
                if flow.display_name == "Default Start Flow":
                    logger.info(f"✓ Found Default Start Flow: {flow.name}")
                    return flow.name

            logger.error("✗ Default Start Flow not found")
            return None

        except Exception as e:
            logger.error(f"✗ Error getting Default Start Flow: {e}")
            return None

    def update_start_page(self, flow_name: str) -> bool:
        """
        Update the Default Start Flow with welcome message via event handler.

        Args:
            flow_name: Flow resource name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the flow to update its event handlers
            flow = self.flows_client.get_flow(name=flow_name)

            # Update welcome message to match documentation
            welcome_message = (
                "Welcome to PawConnect! I'm here to help you find your perfect pet companion. "
                "I can help you search for pets, learn about specific animals, schedule visits, "
                "or start an adoption application. What would you like to do?"
            )

            # Check if there's already a welcome event handler
            has_welcome = False
            for i, event_handler in enumerate(flow.event_handlers):
                if event_handler.event == "sys.no-match-default" or event_handler.event == "sys.no-input-default":
                    # Update existing handler
                    flow.event_handlers[i].trigger_fulfillment = Fulfillment(
                        messages=[
                            ResponseMessage(
                                text=ResponseMessage.Text(text=[welcome_message])
                            )
                        ]
                    )
                    has_welcome = True
                    break

            # If no event handler exists, we'll just log info
            # The welcome message should be set manually or via the START page directly
            if not has_welcome:
                logger.info("ℹ No event handlers found for welcome message")
                logger.info("  The welcome message should be configured in the Dialogflow Console")
                logger.info("  by editing the Default Start Flow's START page entry fulfillment")
                return True  # Non-blocking

            # Update the flow
            updated_flow = self.flows_client.update_flow(flow=flow)
            logger.info(f"✓ Updated flow event handlers with welcome message")
            return True

        except Exception as e:
            logger.error(f"✗ Error updating flow: {e}")
            logger.info("ℹ Configure the welcome message in the Dialogflow Console:")
            logger.info("  Navigate to: Default Start Flow → START page → Entry fulfillment")
            logger.info(f"  Message: '{welcome_message}'")
            return True  # Non-blocking - don't fail the entire setup

    def create_page(
        self,
        flow_name: str,
        display_name: str,
        webhook_name: Optional[str] = None,
        webhook_tag: Optional[str] = None,
        parameters: Optional[List[Dict]] = None,
        entry_messages: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create a page with form parameters and webhook fulfillment.

        Args:
            flow_name: Parent flow resource name
            display_name: Page display name
            webhook_name: Webhook resource name
            webhook_tag: Webhook tag for routing
            parameters: List of parameter definitions
            entry_messages: Optional entry fulfillment messages

        Returns:
            Page resource name or None if creation failed
        """
        try:
            # Check if page already exists
            pages = self.pages_client.list_pages(parent=flow_name)
            existing_page = None
            for page in pages:
                if page.display_name == display_name:
                    existing_page = page
                    break

            # Build or update page
            if existing_page:
                logger.info(f"⚠ Page '{display_name}' already exists, updating...")
                page = existing_page
                # Clear existing transition routes - they will be recreated by the automation
                page.transition_routes.clear()
            else:
                page = Page(display_name=display_name)

            # Add entry fulfillment if messages or webhook provided
            if entry_messages or webhook_name:
                fulfillment_messages = []
                if entry_messages:
                    for msg in entry_messages:
                        fulfillment_messages.append(
                            ResponseMessage(text=ResponseMessage.Text(text=[msg]))
                        )

                page.entry_fulfillment = Fulfillment(
                    messages=fulfillment_messages,
                    webhook=webhook_name if webhook_name else None,
                    tag=webhook_tag if webhook_tag else None
                )

            # Add form parameters
            if parameters:
                form_parameters = []
                for param in parameters:
                    form_param = Form.Parameter(
                        display_name=param["name"],
                        entity_type=param["type"],
                        required=param.get("required", False),
                        redact=param.get("redact", False)
                    )

                    # Add fill behavior with prompt
                    if "prompt" in param:
                        form_param.fill_behavior = Form.Parameter.FillBehavior(
                            initial_prompt_fulfillment=Fulfillment(
                                messages=[
                                    ResponseMessage(
                                        text=ResponseMessage.Text(text=[param["prompt"]])
                                    )
                                ]
                            )
                        )

                    form_parameters.append(form_param)

                page.form = Form(parameters=form_parameters)

            # Create or update the page
            if existing_page:
                updated_page = self.pages_client.update_page(page=page)
                logger.info(f"✓ Updated page: {display_name}")
                return updated_page.name
            else:
                created_page = self.pages_client.create_page(
                    parent=flow_name,
                    page=page
                )
                logger.info(f"✓ Created page: {display_name}")
                return created_page.name

        except Exception as e:
            logger.error(f"✗ Error creating/updating page '{display_name}': {e}")
            return None

    def create_transition_route(
        self,
        parent: str,
        intent: Optional[str] = None,
        condition: Optional[str] = None,
        target_page: Optional[str] = None,
        target_flow: Optional[str] = None,
        trigger_fulfillment: Optional[Fulfillment] = None
    ) -> bool:
        """
        Create a transition route between pages.

        Args:
            parent: Parent resource (flow or page)
            intent: Intent display name to match
            condition: Condition expression to match
            target_page: Target page resource name
            target_flow: Target flow resource name
            trigger_fulfillment: Optional fulfillment to trigger

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build intent path if provided
            intent_path = None
            if intent:
                intent_path = f"{self.agent_path}/intents/{intent}"

            # Create route
            route = TransitionRoute(
                intent=intent_path if intent_path else None,
                condition=condition if condition else None,
                target_page=target_page if target_page else None,
                target_flow=target_flow if target_flow else None,
                trigger_fulfillment=trigger_fulfillment if trigger_fulfillment else None
            )

            # Get parent resource to update
            if "/pages/" in parent:
                # Update page's transition routes
                page = self.pages_client.get_page(name=parent)
                page.transition_routes.append(route)
                self.pages_client.update_page(page=page)
                logger.info(f"✓ Created transition route on page")
            else:
                # Update flow's transition routes
                flow = self.flows_client.get_flow(name=parent)
                flow.transition_routes.append(route)
                self.flows_client.update_flow(flow=flow)
                logger.info(f"✓ Created transition route on flow")

            return True

        except Exception as e:
            logger.error(f"✗ Error creating transition route: {e}")
            return False

    def setup_pawconnect_agent(self) -> bool:
        """
        Complete setup for PawConnect agent including all pages, flows, and routes.

        Returns:
            True if successful, False otherwise
        """
        logger.info("========================================")
        logger.info("Starting PawConnect Agent Automation")
        logger.info("========================================")

        # Step 1: Verify agent
        if not self.verify_agent():
            logger.error("✗ Agent verification failed")
            return False

        # Step 2: Create webhook
        logger.info("\n--- Creating Webhook ---")
        webhook_name = self.create_webhook("PawConnect Webhook")

        # Step 3: Get Default Start Flow
        logger.info("\n--- Getting Default Start Flow ---")
        flow_name = self.get_default_start_flow()
        if not flow_name:
            return False

        # Step 4: Update START_PAGE
        logger.info("\n--- Updating START_PAGE ---")
        if not self.update_start_page(flow_name):
            logger.warning("⚠ Failed to update START_PAGE")

        # Step 5: Create pages
        logger.info("\n--- Creating Pages ---")

        # Check for custom entity types
        logger.info("Checking for custom entity types...")
        pet_species_type = self.get_entity_type_name("pet_species")
        housing_type_type = self.get_entity_type_name("housing_type")

        if not pet_species_type:
            logger.warning("⚠ Entity type 'pet_species' not found")
            logger.info("  → Pet Search page will be created without the 'species' parameter")
            logger.info("  → Run the bash setup script or create entity types manually in Console")

        if not housing_type_type:
            logger.warning("⚠ Entity type 'housing_type' not found")
            logger.info("  → Get Recommendations page will be created without the 'housing_type' parameter")
            logger.info("  → Run the bash setup script or create entity types manually in Console")

        if pet_species_type and housing_type_type:
            logger.info("✓ All custom entity types found")

        # Pet Search Page
        pet_search_params = []
        if pet_species_type:
            pet_search_params.append({
                "name": "species",
                "type": pet_species_type,
                "required": False,
                "prompt": "What species are you interested in?"
            })
        pet_search_params.extend([
            {
                "name": "breed",
                "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                "required": False,
                "prompt": "Do you have a specific breed in mind?"
            },
            {
                "name": "location",
                "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                "required": True,
                "prompt": "What location are you searching in? Please provide your ZIP code or city."
            }
        ])

        pet_search_page = self.create_page(
            flow_name=flow_name,
            display_name="Pet Search",
            webhook_name=webhook_name,
            webhook_tag="search-pets",
            parameters=pet_search_params
        )

        # Pet Details Page
        # Note: No webhook in entry_fulfillment - webhook is called after pet_id is collected
        pet_details_page = self.create_page(
            flow_name=flow_name,
            display_name="Pet Details",
            # Don't set webhook in entry_fulfillment - it will be called after parameter collection
            webhook_name=None,
            webhook_tag=None,
            parameters=[
                {
                    "name": "pet_id",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                    "required": True,
                    "prompt": "Which pet would you like to learn more about? Please provide the pet ID."
                }
            ]
        )

        # Get Recommendations Page
        recommendations_params = [
            {
                "name": "location",
                "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                "required": True,
                "prompt": "What's your ZIP code or city?"
            }
        ]
        if housing_type_type:
            recommendations_params.append({
                "name": "housing_type",
                "type": housing_type_type,
                "required": False,
                "prompt": "What type of housing do you have?"
            })
        recommendations_params.append({
            "name": "has_children",
            "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
            "required": False,
            "prompt": "Do you have children at home?"
        })

        recommendations_page = self.create_page(
            flow_name=flow_name,
            display_name="Get Recommendations",
            webhook_name=webhook_name,
            webhook_tag="get-recommendations",
            parameters=recommendations_params
        )

        # Schedule Visit Page
        schedule_visit_page = self.create_page(
            flow_name=flow_name,
            display_name="Schedule Visit",
            webhook_name=webhook_name,
            webhook_tag="schedule-visit",
            parameters=[
                {
                    "name": "visit_date",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.date",
                    "required": True,
                    "prompt": "What date would you like to schedule your visit?"
                },
                {
                    "name": "visit_time",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.time",
                    "required": True,
                    "prompt": "What time works best for you?"
                },
                {
                    "name": "visitor_name",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                    "required": True,
                    "prompt": "May I have your full name?"
                },
                {
                    "name": "visitor_email",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.any",
                    "required": True,
                    "redact": True,
                    "prompt": "What's your email address?"
                },
                {
                    "name": "visitor_phone",
                    "type": "projects/-/locations/-/agents/-/entityTypes/sys.phone-number",
                    "required": True,
                    "redact": True,
                    "prompt": "What's your phone number?"
                }
            ]
        )

        # Adoption Application Page
        adoption_page = self.create_page(
            flow_name=flow_name,
            display_name="Adoption Application",
            webhook_name=webhook_name,
            webhook_tag="submit-application"
        )

        # Foster Application Page
        foster_page = self.create_page(
            flow_name=flow_name,
            display_name="Foster Application",
            webhook_name=webhook_name,
            webhook_tag="submit-application"
        )

        # Step 6: Create transition routes
        logger.info("\n--- Creating Transition Routes ---")

        # Look up required intents
        logger.info("Looking up intents...")
        intent_search_pets = self.get_intent_name("intent.search_pets")
        intent_get_recommendations = self.get_intent_name("intent.get_recommendations")
        intent_schedule_visit = self.get_intent_name("intent.schedule_visit")
        intent_adoption = self.get_intent_name("intent.adoption_application")
        intent_foster = self.get_intent_name("intent.foster_application")

        routes_created = 0
        routes_skipped = 0

        # Create flow-level routes (from START to pages)
        if intent_search_pets and pet_search_page:
            try:
                flow = self.flows_client.get_flow(name=flow_name)

                # Create route with parameter presets to pass intent parameters to page parameters
                # This allows "I want to adopt a dog in Seattle" to automatically fill location
                route = TransitionRoute(
                    intent=intent_search_pets,
                    target_page=pet_search_page,
                    trigger_fulfillment=Fulfillment(
                        set_parameter_actions=[
                            Fulfillment.SetParameterAction(
                                parameter="location",
                                value="$session.params.location"
                            ),
                            Fulfillment.SetParameterAction(
                                parameter="species",
                                value="$session.params.species"
                            ),
                            Fulfillment.SetParameterAction(
                                parameter="breed",
                                value="$session.params.breed"
                            )
                        ]
                    )
                )

                # Check if route already exists
                route_exists = any(
                    r.intent == intent_search_pets and r.target_page == pet_search_page
                    for r in flow.transition_routes
                )

                if not route_exists:
                    flow.transition_routes.append(route)
                    self.flows_client.update_flow(flow=flow)
                    logger.info("✓ Created route: START → Pet Search (with parameter presets)")
                    routes_created += 1
                else:
                    logger.info("⚠ Route START → Pet Search already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create route START → Pet Search: {e}")
                routes_skipped += 1
        else:
            logger.warning("⚠ Cannot create route START → Pet Search (missing intent or page)")
            routes_skipped += 1

        if intent_get_recommendations and recommendations_page:
            try:
                flow = self.flows_client.get_flow(name=flow_name)

                # Create route with parameter presets to pass intent parameters to page parameters
                route = TransitionRoute(
                    intent=intent_get_recommendations,
                    target_page=recommendations_page,
                    trigger_fulfillment=Fulfillment(
                        set_parameter_actions=[
                            Fulfillment.SetParameterAction(
                                parameter="location",
                                value="$session.params.location"
                            ),
                            Fulfillment.SetParameterAction(
                                parameter="housing_type",
                                value="$session.params.housing_type"
                            ),
                            Fulfillment.SetParameterAction(
                                parameter="has_children",
                                value="$session.params.has_children"
                            )
                        ]
                    )
                )

                route_exists = any(
                    r.intent == intent_get_recommendations and r.target_page == recommendations_page
                    for r in flow.transition_routes
                )

                if not route_exists:
                    flow.transition_routes.append(route)
                    self.flows_client.update_flow(flow=flow)
                    logger.info("✓ Created route: START → Get Recommendations (with parameter presets)")
                    routes_created += 1
                else:
                    logger.info("⚠ Route START → Get Recommendations already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create route START → Get Recommendations: {e}")
                routes_skipped += 1
        else:
            logger.warning("⚠ Cannot create route START → Get Recommendations (missing intent or page)")
            routes_skipped += 1

        # Create page-level routes (from Pet Details to other pages)
        if pet_details_page:
            if intent_schedule_visit and schedule_visit_page:
                try:
                    page = self.pages_client.get_page(name=pet_details_page)
                    route = TransitionRoute(intent=intent_schedule_visit, target_page=schedule_visit_page)

                    route_exists = any(
                        r.intent == intent_schedule_visit and r.target_page == schedule_visit_page
                        for r in page.transition_routes
                    )

                    if not route_exists:
                        page.transition_routes.append(route)
                        self.pages_client.update_page(page=page)
                        logger.info("✓ Created route: Pet Details → Schedule Visit")
                        routes_created += 1
                    else:
                        logger.info("⚠ Route Pet Details → Schedule Visit already exists")
                except Exception as e:
                    logger.warning(f"⚠ Failed to create route Pet Details → Schedule Visit: {e}")
                    routes_skipped += 1
            else:
                logger.warning("⚠ Cannot create route Pet Details → Schedule Visit (missing intent or page)")
                routes_skipped += 1

            if intent_adoption and adoption_page:
                try:
                    page = self.pages_client.get_page(name=pet_details_page)
                    route = TransitionRoute(intent=intent_adoption, target_page=adoption_page)

                    route_exists = any(
                        r.intent == intent_adoption and r.target_page == adoption_page
                        for r in page.transition_routes
                    )

                    if not route_exists:
                        page.transition_routes.append(route)
                        self.pages_client.update_page(page=page)
                        logger.info("✓ Created route: Pet Details → Adoption Application")
                        routes_created += 1
                    else:
                        logger.info("⚠ Route Pet Details → Adoption Application already exists")
                except Exception as e:
                    logger.warning(f"⚠ Failed to create route Pet Details → Adoption Application: {e}")
                    routes_skipped += 1
            else:
                logger.warning("⚠ Cannot create route Pet Details → Adoption (missing intent or page)")
                routes_skipped += 1

            if intent_foster and foster_page:
                try:
                    page = self.pages_client.get_page(name=pet_details_page)
                    route = TransitionRoute(intent=intent_foster, target_page=foster_page)

                    route_exists = any(
                        r.intent == intent_foster and r.target_page == foster_page
                        for r in page.transition_routes
                    )

                    if not route_exists:
                        page.transition_routes.append(route)
                        self.pages_client.update_page(page=page)
                        logger.info("✓ Created route: Pet Details → Foster Application")
                        routes_created += 1
                    else:
                        logger.info("⚠ Route Pet Details → Foster Application already exists")
                except Exception as e:
                    logger.warning(f"⚠ Failed to create route Pet Details → Foster Application: {e}")
                    routes_skipped += 1
            else:
                logger.warning("⚠ Cannot create route Pet Details → Foster (missing intent or page)")
                routes_skipped += 1

        # Pet Search completion - show results and restart flow
        # The webhook will return search results to display to the user
        # Transitioning back to the flow restarts conversation from beginning
        if pet_search_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=pet_search_page)

                # Route when form is filled - call webhook to show search results
                # Webhook will provide the response message with search results
                # Transition back to flow to restart conversation
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="search-pets"
                    ),
                    target_flow=flow_name  # Restart the flow from beginning
                )

                route_exists = any(
                    r.condition == "$page.params.status = \"FINAL\""
                    for r in page.transition_routes
                )

                if not route_exists:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info("✓ Created completion route: Pet Search → Flow Restart (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Pet Search already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Pet Search: {e}")
                routes_skipped += 1
        else:
            logger.warning("⚠ Cannot create completion route for Pet Search (missing page or webhook)")
            routes_skipped += 1

        # Pet Details - call webhook after pet_id is collected, then restart flow
        if pet_details_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=pet_details_page)

                # Route when pet_id is collected - call webhook to fetch pet details
                # Webhook will provide the pet details response
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="get-pet-details"
                    ),
                    target_flow=flow_name  # Restart the flow from beginning
                )

                route_exists = any(
                    r.condition == "$page.params.status = \"FINAL\""
                    for r in page.transition_routes
                )

                if not route_exists:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info(f"✓ Created completion route: Pet Details → {'Start' if start_page else 'End'} (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Pet Details already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Pet Details: {e}")
                routes_skipped += 1
        else:
            logger.warning("⚠ Cannot create completion route for Pet Details (missing page or webhook)")
            routes_skipped += 1

        # Get Recommendations completion - show recommendations and restart flow
        # User can then continue the conversation naturally
        if recommendations_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=recommendations_page)

                # Route when form is filled - call webhook to get recommendations
                # Webhook will provide personalized recommendations response
                # Transition back to flow to restart conversation
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="get-recommendations"
                        # No messages - let webhook provide the recommendations
                    ),
                    target_flow=flow_name  # Restart the flow from beginning
                )

                route_exists = any(
                    r.condition == "$page.params.status = \"FINAL\""
                    for r in page.transition_routes
                )

                if not route_exists:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info("✓ Created completion route: Get Recommendations → Flow Restart (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Get Recommendations already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Get Recommendations: {e}")
                routes_skipped += 1
        else:
            logger.warning("⚠ Cannot create completion route for Get Recommendations (missing page or webhook)")
            routes_skipped += 1

        # Add end-of-conversation routes for terminal pages
        # Schedule Visit → End (after form is submitted)
        if schedule_visit_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=schedule_visit_page)
                # Route when form is completed - call webhook to schedule visit
                # Webhook will provide confirmation message with visit details
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="schedule-visit"
                        # No messages - let webhook provide dynamic confirmation
                    )
                )

                # Check if similar route exists
                has_completion_route = any(
                    r.condition and "FINAL" in r.condition
                    for r in page.transition_routes
                )

                if not has_completion_route:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info("✓ Created completion route: Schedule Visit → End (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Schedule Visit already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Schedule Visit: {e}")
                routes_skipped += 1

        # Adoption Application → End (after form is submitted)
        if adoption_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=adoption_page)
                # Route when application is submitted - call webhook to submit application
                # Webhook will provide confirmation message
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="submit-application"
                        # No messages - let webhook provide dynamic confirmation
                    )
                )

                has_completion_route = any(
                    r.condition and "FINAL" in r.condition
                    for r in page.transition_routes
                )

                if not has_completion_route:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info("✓ Created completion route: Adoption Application → End (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Adoption Application already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Adoption Application: {e}")
                routes_skipped += 1

        # Foster Application → End (after form is submitted)
        if foster_page and webhook_name:
            try:
                page = self.pages_client.get_page(name=foster_page)
                # Route when application is submitted - call webhook to submit application
                # Webhook will provide confirmation message
                route = TransitionRoute(
                    condition="$page.params.status = \"FINAL\"",
                    trigger_fulfillment=Fulfillment(
                        webhook=webhook_name,
                        tag="submit-application"
                        # No messages - let webhook provide dynamic confirmation
                    )
                )

                has_completion_route = any(
                    r.condition and "FINAL" in r.condition
                    for r in page.transition_routes
                )

                if not has_completion_route:
                    page.transition_routes.append(route)
                    self.pages_client.update_page(page=page)
                    logger.info("✓ Created completion route: Foster Application → End (with webhook)")
                    routes_created += 1
                else:
                    logger.info("⚠ Completion route for Foster Application already exists")
            except Exception as e:
                logger.warning(f"⚠ Failed to create completion route for Foster Application: {e}")
                routes_skipped += 1

        logger.info(f"\nTransition routes summary: {routes_created} created, {routes_skipped} skipped or failed")

        if routes_skipped > 0:
            logger.info("\n💡 Tip: Run the bash setup script to create missing intents, or add them manually in Console")

        logger.info("\n========================================")
        logger.info("✓ PawConnect Agent Automation Complete!")
        logger.info("========================================")
        logger.info("\nNext Steps:")
        step_num = 1
        if routes_skipped > 0:
            logger.info(f"{step_num}. Add missing transition routes in Dialogflow Console (if not auto-created)")
            step_num += 1
        logger.info(f"{step_num}. Test your agent in the Dialogflow CX Simulator")
        logger.info(f"{step_num + 1}. Configure additional flow logic and refine fulfillments as needed")
        logger.info(f"{step_num + 2}. Set up the welcome message in START page entry fulfillment if needed")

        return True


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automate Dialogflow CX agent setup for PawConnect"
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID"
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Dialogflow CX agent ID"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Agent location (default: us-central1)"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL (e.g., https://your-cloud-run-url/webhook)"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="INFO"
    )

    # Run automation
    automation = DialogflowAutomation(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location,
        webhook_url=args.webhook_url
    )

    success = automation.setup_pawconnect_agent()

    if success:
        logger.info("\n✓ Setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n✗ Setup failed. Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
