#!/usr/bin/env python3
"""
Add transition routes to Dialogflow CX pages with intent matchers.
This script should be run after the main setup to connect pages together.
"""

import sys
from typing import Dict, List, Optional
from google.cloud.dialogflowcx_v3 import (
    IntentsClient,
    FlowsClient,
    PagesClient,
)
from google.cloud.dialogflowcx_v3.types import (
    Page,
    TransitionRoute,
    Fulfillment,
)
from loguru import logger


class TransitionRouteManager:
    """Manages transition routes between pages."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        location: str = "us-central1"
    ):
        """
        Initialize transition route manager.

        Args:
            project_id: GCP project ID
            agent_id: Dialogflow CX agent ID
            location: Agent location
        """
        self.project_id = project_id
        self.agent_id = agent_id
        self.location = location
        self.agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"

        # Initialize clients
        self.intents_client = IntentsClient()
        self.flows_client = FlowsClient()
        self.pages_client = PagesClient()

        # Cache for intent and page lookups
        self._intent_cache = {}
        self._page_cache = {}

    def get_intent_by_name(self, display_name: str) -> Optional[str]:
        """
        Get intent resource name by display name.

        Args:
            display_name: Intent display name

        Returns:
            Intent resource name or None if not found
        """
        if display_name in self._intent_cache:
            return self._intent_cache[display_name]

        try:
            intents = self.intents_client.list_intents(parent=self.agent_path)
            for intent in intents:
                if intent.display_name == display_name:
                    self._intent_cache[display_name] = intent.name
                    return intent.name

            logger.warning(f"⚠ Intent not found: {display_name}")
            return None

        except Exception as e:
            logger.error(f"✗ Error getting intent '{display_name}': {e}")
            return None

    def get_page_by_name(self, flow_name: str, display_name: str) -> Optional[str]:
        """
        Get page resource name by display name.

        Args:
            flow_name: Parent flow resource name
            display_name: Page display name

        Returns:
            Page resource name or None if not found
        """
        cache_key = f"{flow_name}:{display_name}"
        if cache_key in self._page_cache:
            return self._page_cache[cache_key]

        try:
            pages = self.pages_client.list_pages(parent=flow_name)
            for page in pages:
                if page.display_name == display_name:
                    self._page_cache[cache_key] = page.name
                    return page.name

            logger.warning(f"⚠ Page not found: {display_name}")
            return None

        except Exception as e:
            logger.error(f"✗ Error getting page '{display_name}': {e}")
            return None

    def get_default_start_flow(self) -> Optional[str]:
        """Get the Default Start Flow resource name."""
        try:
            flows = self.flows_client.list_flows(parent=self.agent_path)
            for flow in flows:
                if flow.display_name == "Default Start Flow":
                    return flow.name
            return None
        except Exception as e:
            logger.error(f"✗ Error getting Default Start Flow: {e}")
            return None

    def add_route_to_page(
        self,
        page_name: str,
        intent_display_name: Optional[str] = None,
        condition: Optional[str] = None,
        target_page_name: Optional[str] = None,
        messages: Optional[List[str]] = None
    ) -> bool:
        """
        Add a transition route to a specific page.

        Args:
            page_name: Source page resource name
            intent_display_name: Intent display name to match
            condition: Condition expression to match
            target_page_name: Target page resource name
            messages: Optional messages to display during transition

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the page
            page = self.pages_client.get_page(name=page_name)

            # Get intent if provided
            intent_name = None
            if intent_display_name:
                intent_name = self.get_intent_by_name(intent_display_name)
                if not intent_name:
                    logger.error(f"✗ Cannot create route: intent not found")
                    return False

            # Build route
            route = TransitionRoute(
                intent=intent_name if intent_name else None,
                condition=condition if condition else None,
                target_page=target_page_name if target_page_name else None
            )

            # Add messages if provided
            if messages:
                fulfillment_messages = []
                for msg in messages:
                    fulfillment_messages.append(
                        Fulfillment.Message(text=Fulfillment.Text(text=[msg]))
                    )
                route.trigger_fulfillment = Fulfillment(messages=fulfillment_messages)

            # Add route to page
            page.transition_routes.append(route)

            # Update page
            self.pages_client.update_page(page=page)

            logger.info(f"✓ Added route to page: {page.display_name}")
            return True

        except Exception as e:
            logger.error(f"✗ Error adding route to page: {e}")
            return False

    def add_route_to_flow(
        self,
        flow_name: str,
        intent_display_name: Optional[str] = None,
        condition: Optional[str] = None,
        target_page_name: Optional[str] = None,
        messages: Optional[List[str]] = None
    ) -> bool:
        """
        Add a transition route to a flow (applies from START_PAGE).

        Args:
            flow_name: Flow resource name
            intent_display_name: Intent display name to match
            condition: Condition expression to match
            target_page_name: Target page resource name
            messages: Optional messages to display during transition

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the flow
            flow = self.flows_client.get_flow(name=flow_name)

            # Get intent if provided
            intent_name = None
            if intent_display_name:
                intent_name = self.get_intent_by_name(intent_display_name)
                if not intent_name:
                    logger.error(f"✗ Cannot create route: intent not found")
                    return False

            # Build route
            route = TransitionRoute(
                intent=intent_name if intent_name else None,
                condition=condition if condition else None,
                target_page=target_page_name if target_page_name else None
            )

            # Add messages if provided
            if messages:
                fulfillment_messages = []
                for msg in messages:
                    fulfillment_messages.append(
                        Fulfillment.Message(text=Fulfillment.Text(text=[msg]))
                    )
                route.trigger_fulfillment = Fulfillment(messages=fulfillment_messages)

            # Add route to flow
            flow.transition_routes.append(route)

            # Update flow
            self.flows_client.update_flow(flow=flow)

            logger.info(f"✓ Added route to flow: {flow.display_name}")
            return True

        except Exception as e:
            logger.error(f"✗ Error adding route to flow: {e}")
            return False

    def setup_pawconnect_routes(self) -> bool:
        """
        Set up all transition routes for PawConnect agent.

        Returns:
            True if successful, False otherwise
        """
        logger.info("========================================")
        logger.info("Adding Transition Routes")
        logger.info("========================================")

        # Get Default Start Flow
        flow_name = self.get_default_start_flow()
        if not flow_name:
            logger.error("✗ Cannot find Default Start Flow")
            return False

        # Get page names
        pet_search_page = self.get_page_by_name(flow_name, "Pet Search")
        pet_details_page = self.get_page_by_name(flow_name, "Pet Details")
        recommendations_page = self.get_page_by_name(flow_name, "Get Recommendations")
        schedule_visit_page = self.get_page_by_name(flow_name, "Schedule Visit")
        adoption_page = self.get_page_by_name(flow_name, "Adoption Application")
        foster_page = self.get_page_by_name(flow_name, "Foster Application")

        # Check all pages exist
        if not all([pet_search_page, pet_details_page, recommendations_page,
                    schedule_visit_page, adoption_page, foster_page]):
            logger.error("✗ Not all pages found. Run setup_dialogflow_automation.py first.")
            return False

        success = True

        # Route 1: START_PAGE → Pet Search (intent.search_pets)
        logger.info("\n--- Adding route: START_PAGE → Pet Search ---")
        if not self.add_route_to_flow(
            flow_name=flow_name,
            intent_display_name="intent.search_pets",
            target_page_name=pet_search_page
        ):
            success = False

        # Route 2: START_PAGE → Get Recommendations (intent.get_recommendations)
        logger.info("\n--- Adding route: START_PAGE → Get Recommendations ---")
        if not self.add_route_to_flow(
            flow_name=flow_name,
            intent_display_name="intent.get_recommendations",
            target_page_name=recommendations_page
        ):
            success = False

        # Route 3: Pet Search → Pet Details (condition-based on parameters filled)
        logger.info("\n--- Adding route: Pet Search → Pet Details ---")
        if not self.add_route_to_page(
            page_name=pet_search_page,
            condition='$page.params.status = "FINAL"',
            target_page_name=pet_details_page
        ):
            success = False

        # Route 4: Get Recommendations → Pet Details (condition-based)
        logger.info("\n--- Adding route: Get Recommendations → Pet Details ---")
        if not self.add_route_to_page(
            page_name=recommendations_page,
            condition='$page.params.status = "FINAL"',
            target_page_name=pet_details_page
        ):
            success = False

        # Route 5: Pet Details → Schedule Visit (intent.schedule_visit)
        logger.info("\n--- Adding route: Pet Details → Schedule Visit ---")
        if not self.add_route_to_page(
            page_name=pet_details_page,
            intent_display_name="intent.schedule_visit",
            target_page_name=schedule_visit_page
        ):
            success = False

        # Route 6: Pet Details → Adoption Application (intent.adoption_application)
        logger.info("\n--- Adding route: Pet Details → Adoption Application ---")
        if not self.add_route_to_page(
            page_name=pet_details_page,
            intent_display_name="intent.adoption_application",
            target_page_name=adoption_page
        ):
            success = False

        # Route 7: Pet Details → Foster Application (intent.foster_application)
        logger.info("\n--- Adding route: Pet Details → Foster Application ---")
        if not self.add_route_to_page(
            page_name=pet_details_page,
            intent_display_name="intent.foster_application",
            target_page_name=foster_page
        ):
            success = False

        if success:
            logger.info("\n✓ All transition routes added successfully!")
        else:
            logger.warning("\n⚠ Some routes failed. Check the logs above.")

        return success


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add transition routes to PawConnect Dialogflow CX agent"
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

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="INFO"
    )

    # Run route setup
    route_manager = TransitionRouteManager(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    success = route_manager.setup_pawconnect_routes()

    if success:
        logger.info("\n✓ Transition routes configured successfully!")
        logger.info("\nNext Steps:")
        logger.info("1. Test your agent in the Dialogflow CX Simulator")
        logger.info("2. Verify all intents are routing correctly")
        logger.info("3. Adjust parameters and conditions as needed")
        sys.exit(0)
    else:
        logger.error("\n✗ Failed to configure all routes. Check the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
