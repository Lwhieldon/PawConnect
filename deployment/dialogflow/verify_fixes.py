#!/usr/bin/env python3
"""
Verify Dialogflow CX Configuration
This script checks whether all fixes have been applied correctly.
"""

import sys
from google.cloud.dialogflowcx_v3 import (
    IntentsClient,
    EntityTypesClient,
    PagesClient,
    FlowsClient
)
from google.api_core.client_options import ClientOptions
from loguru import logger


def verify_intent_training_phrases(
    project_id: str,
    agent_id: str,
    location: str = "us-central1"
) -> bool:
    """Verify intent.get_recommendations has affirmative training phrases."""
    try:
        agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        intents_client = IntentsClient(client_options=client_options)

        logger.info("Checking intent.get_recommendations training phrases...")

        # Find the intent
        intents_list = list(intents_client.list_intents(parent=agent_path))
        get_recommendations_intent = None

        for intent in intents_list:
            if intent.display_name == "intent.get_recommendations":
                get_recommendations_intent = intent
                break

        if not get_recommendations_intent:
            logger.error("✗ intent.get_recommendations NOT FOUND")
            return False

        logger.info(f"✓ Found intent: {get_recommendations_intent.name}")

        # Check training phrases
        training_phrases = get_recommendations_intent.training_phrases
        logger.info(f"  Training phrases count: {len(training_phrases)}")

        # Look for affirmative responses
        affirmative_found = False
        for phrase in training_phrases:
            text = "".join([part.text for part in phrase.parts])
            logger.info(f"  - '{text}'")
            if text.lower() in ["yes", "yes please", "sure"]:
                affirmative_found = True

        if affirmative_found:
            logger.info("✓ Affirmative responses found in training phrases")
            return True
        else:
            logger.error("✗ Affirmative responses NOT found in training phrases")
            logger.error("  Missing: 'Yes', 'Yes please', 'Sure'")
            return False

    except Exception as e:
        logger.error(f"✗ Error verifying intent: {e}")
        return False


def verify_housing_entity(
    project_id: str,
    agent_id: str,
    location: str = "us-central1"
) -> bool:
    """Verify housing_type entity has apartment, house, condo."""
    try:
        agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        entity_types_client = EntityTypesClient(client_options=client_options)

        logger.info("Checking housing_type entity...")

        # Find the entity type
        entity_types_list = list(entity_types_client.list_entity_types(parent=agent_path))
        housing_type_entity = None

        for entity_type in entity_types_list:
            if entity_type.display_name == "housing_type":
                housing_type_entity = entity_type
                break

        if not housing_type_entity:
            logger.error("✗ housing_type entity NOT FOUND")
            return False

        logger.info(f"✓ Found entity: {housing_type_entity.name}")

        # Check entities
        entities = housing_type_entity.entities
        logger.info(f"  Entities count: {len(entities)}")

        required_values = ["apartment", "house", "condo"]
        found_values = [entity.value for entity in entities]

        all_found = True
        for required in required_values:
            if required in found_values:
                entity = next(e for e in entities if e.value == required)
                logger.info(f"  ✓ {required}: {entity.synonyms}")
            else:
                logger.error(f"  ✗ {required}: NOT FOUND")
                all_found = False

        return all_found

    except Exception as e:
        logger.error(f"✗ Error verifying entity: {e}")
        return False


def verify_search_pets_intent(
    project_id: str,
    agent_id: str,
    location: str = "us-central1"
) -> bool:
    """Verify intent.search_pets has parameter-annotated training phrases."""
    try:
        agent_path = f"projects/{project_id}/locations/{location}/agents/{agent_id}"
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        intents_client = IntentsClient(client_options=client_options)

        logger.info("Checking intent.search_pets parameter annotations...")

        # Find the intent
        intents_list = list(intents_client.list_intents(parent=agent_path))
        search_pets_intent = None

        for intent in intents_list:
            if intent.display_name == "intent.search_pets":
                search_pets_intent = intent
                break

        if not search_pets_intent:
            logger.error("✗ intent.search_pets NOT FOUND")
            return False

        logger.info(f"✓ Found intent: {search_pets_intent.name}")

        # Check parameters
        parameters = search_pets_intent.parameters
        logger.info(f"  Parameters count: {len(parameters)}")

        required_params = ["location", "species"]
        found_params = [param.id for param in parameters]

        all_found = True
        for required in required_params:
            if required in found_params:
                param = next(p for p in parameters if p.id == required)
                logger.info(f"  ✓ {required}: {param.entity_type}")
            else:
                logger.error(f"  ✗ {required}: NOT FOUND")
                all_found = False

        # Check for parameter annotations in training phrases
        has_annotations = False
        for phrase in search_pets_intent.training_phrases:
            for part in phrase.parts:
                if part.parameter_id:
                    has_annotations = True
                    text = part.text
                    param_id = part.parameter_id
                    logger.info(f"  - '{text}' → @{param_id}")
                    break
            if has_annotations:
                break

        if has_annotations:
            logger.info("✓ Parameter annotations found in training phrases")
        else:
            logger.error("✗ No parameter annotations found in training phrases")
            all_found = False

        return all_found

    except Exception as e:
        logger.error(f"✗ Error verifying intent: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify Dialogflow CX configuration"
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

    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  Dialogflow CX Configuration Check    ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")
    logger.info(f"Project ID: {args.project_id}")
    logger.info(f"Agent ID: {args.agent_id}")
    logger.info(f"Location: {args.location}")
    logger.info("")

    # Run all checks
    logger.info("========================================")
    logger.info("Check 1: intent.search_pets")
    logger.info("========================================")
    logger.info("")
    check1 = verify_search_pets_intent(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    logger.info("")
    logger.info("========================================")
    logger.info("Check 2: intent.get_recommendations")
    logger.info("========================================")
    logger.info("")
    check2 = verify_intent_training_phrases(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    logger.info("")
    logger.info("========================================")
    logger.info("Check 3: housing_type entity")
    logger.info("========================================")
    logger.info("")
    check3 = verify_housing_entity(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    # Summary
    logger.info("")
    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  Verification Results                  ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")

    if check1:
        logger.info("✓ intent.search_pets: PASS")
    else:
        logger.error("✗ intent.search_pets: FAIL")

    if check2:
        logger.info("✓ intent.get_recommendations: PASS")
    else:
        logger.error("✗ intent.get_recommendations: FAIL")

    if check3:
        logger.info("✓ housing_type entity: PASS")
    else:
        logger.error("✗ housing_type entity: FAIL")

    logger.info("")

    if check1 and check2 and check3:
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  ✓ ALL CHECKS PASSED!                 ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        logger.info("Configuration is correct. If you're still")
        logger.info("experiencing issues, try:")
        logger.info("  1. Clear Dialogflow simulator cache")
        logger.info("  2. Wait 2-3 minutes for changes to propagate")
        logger.info("  3. Test in a new browser incognito window")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("╔════════════════════════════════════════╗")
        logger.error("║  ✗ SOME CHECKS FAILED                 ║")
        logger.error("╚════════════════════════════════════════╝")
        logger.error("")
        logger.error("Run fix_parameter_extraction.py to apply fixes:")
        logger.error("")
        logger.error(f"  python deployment/dialogflow/fix_parameter_extraction.py \\")
        logger.error(f"    --project-id {args.project_id} \\")
        logger.error(f"    --agent-id {args.agent_id} \\")
        logger.error(f"    --location {args.location}")
        logger.error("")
        sys.exit(1)


if __name__ == "__main__":
    main()
