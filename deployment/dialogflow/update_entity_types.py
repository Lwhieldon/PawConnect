#!/usr/bin/env python3
"""
Update Dialogflow CX Entity Types
This script updates entity types to include missing synonyms.
"""

import sys
from typing import Optional
from google.cloud.dialogflowcx_v3 import EntityTypesClient
from google.cloud.dialogflowcx_v3.types import EntityType
from google.api_core.client_options import ClientOptions
from loguru import logger


def update_housing_type_entity(
    project_id: str,
    agent_id: str,
    location: str = "us-central1"
) -> bool:
    """
    Update the housing_type entity type to include more housing types.

    Args:
        project_id: GCP project ID
        agent_id: Dialogflow CX agent ID
        location: Agent location

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build agent path
        agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"

        # Build regional API endpoint
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        # Initialize client
        entity_types_client = EntityTypesClient(client_options=client_options)

        logger.info(f"Looking up housing_type entity in agent: {agent_path}")

        # Find the entity type
        entity_types_list = list(entity_types_client.list_entity_types(parent=agent_path))
        housing_type_entity = None

        for entity_type in entity_types_list:
            if entity_type.display_name == "housing_type":
                housing_type_entity = entity_type
                logger.info(f"✓ Found entity type: {entity_type.name}")
                break

        if not housing_type_entity:
            logger.error("✗ Entity type 'housing_type' not found")
            return False

        # Define expanded entities with more housing types
        entities = [
            EntityType.Entity(
                value="apartment",
                synonyms=["apartment", "apt", "flat", "apartments", "apartment building"]
            ),
            EntityType.Entity(
                value="house",
                synonyms=["house", "home", "single family", "single-family home"]
            ),
            EntityType.Entity(
                value="condo",
                synonyms=["condo", "condominium", "townhouse", "townhome"]
            ),
            EntityType.Entity(
                value="own",
                synonyms=["own", "owner", "homeowner", "I own", "own my home"]
            ),
            EntityType.Entity(
                value="rent",
                synonyms=["rent", "renter", "renting", "lease", "I rent", "renting a place"]
            ),
            EntityType.Entity(
                value="live_with_family",
                synonyms=["live with family", "parents", "family home", "with parents", "parents house"]
            )
        ]

        # Update the entity type
        housing_type_entity.entities.clear()
        housing_type_entity.entities.extend(entities)
        housing_type_entity.enable_fuzzy_extraction = True

        # Update the entity type
        updated_entity = entity_types_client.update_entity_type(entity_type=housing_type_entity)

        logger.info(f"✓ Updated entity type with {len(entities)} entities")
        logger.info("  Added: apartment, house, condo")
        logger.info("  Updated: own, rent, live_with_family")

        return True

    except Exception as e:
        logger.error(f"✗ Error updating entity type: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update Dialogflow CX entity types"
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

    logger.info("========================================")
    logger.info("Updating Entity Types")
    logger.info("========================================")
    logger.info("")

    success = update_housing_type_entity(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    if success:
        logger.info("")
        logger.info("========================================")
        logger.info("✓ Entity Type Update Complete!")
        logger.info("========================================")
        logger.info("")
        logger.info("Now users can say:")
        logger.info("  'apartment', 'house', 'condo'")
        logger.info("And Dialogflow will recognize these housing types!")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("✗ Entity type update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
