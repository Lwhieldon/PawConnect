#!/usr/bin/env python3
"""
Update Dialogflow CX Intents with Parameter Annotations
This script adds parameter annotations to training phrases so Dialogflow can extract
parameters like location and species from the user's initial utterance.
"""

import os
import sys
from typing import Optional
from google.cloud.dialogflowcx_v3 import IntentsClient
from google.cloud.dialogflowcx_v3.types import Intent
from google.api_core.client_options import ClientOptions
from loguru import logger


def update_search_pets_intent(
    project_id: str,
    agent_id: str,
    location: str = "us-central1"
) -> bool:
    """
    Update the intent.search_pets intent with parameter annotations.

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
        intents_client = IntentsClient(client_options=client_options)

        logger.info(f"Looking up intent.search_pets in agent: {agent_path}")

        # Find the intent
        intents_list = list(intents_client.list_intents(parent=agent_path))
        search_pets_intent = None

        for intent in intents_list:
            if intent.display_name == "intent.search_pets":
                search_pets_intent = intent
                logger.info(f"✓ Found intent: {intent.name}")
                break

        if not search_pets_intent:
            logger.error("✗ Intent 'intent.search_pets' not found")
            return False

        # Define parameters for the intent
        # These will be extracted from training phrases
        parameters = [
            Intent.Parameter(
                id="species",
                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any"
            ),
            Intent.Parameter(
                id="location",
                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any"
            ),
            Intent.Parameter(
                id="breed",
                entity_type="projects/-/locations/-/agents/-/entityTypes/sys.any"
            )
        ]

        # Define training phrases with parameter annotations
        training_phrases = [
            # With location and species
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I want to adopt a "),
                    Intent.TrainingPhrase.Part(text="dog", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" in "),
                    Intent.TrainingPhrase.Part(text="Seattle", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Show me "),
                    Intent.TrainingPhrase.Part(text="cats", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" near "),
                    Intent.TrainingPhrase.Part(text="Portland", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I'm looking for a "),
                    Intent.TrainingPhrase.Part(text="puppy", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" in "),
                    Intent.TrainingPhrase.Part(text="New York", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Find me a "),
                    Intent.TrainingPhrase.Part(text="kitten", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" around "),
                    Intent.TrainingPhrase.Part(text="Austin", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Search for "),
                    Intent.TrainingPhrase.Part(text="dogs", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" in "),
                    Intent.TrainingPhrase.Part(text="San Francisco", parameter_id="location")
                ],
                repeat_count=1
            ),
            # With location only
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I want to adopt a pet in "),
                    Intent.TrainingPhrase.Part(text="Chicago", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Search for pets near "),
                    Intent.TrainingPhrase.Part(text="Boston", parameter_id="location")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Find pets around "),
                    Intent.TrainingPhrase.Part(text="Denver", parameter_id="location")
                ],
                repeat_count=1
            ),
            # With species only
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I want to search for a "),
                    Intent.TrainingPhrase.Part(text="dog", parameter_id="species")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Show me available "),
                    Intent.TrainingPhrase.Part(text="cats", parameter_id="species")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I'm looking for a "),
                    Intent.TrainingPhrase.Part(text="rabbit", parameter_id="species"),
                    Intent.TrainingPhrase.Part(text=" to adopt")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Find me a "),
                    Intent.TrainingPhrase.Part(text="puppy", parameter_id="species")
                ],
                repeat_count=1
            ),
            # Generic (no parameters)
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I want to search for a pet")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Can you help me find a pet")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Search for pets")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="I'm looking for a rescue animal")
                ],
                repeat_count=1
            ),
            Intent.TrainingPhrase(
                parts=[
                    Intent.TrainingPhrase.Part(text="Help me find a pet to adopt")
                ],
                repeat_count=1
            )
        ]

        # Update the intent with new training phrases and parameters
        search_pets_intent.training_phrases.clear()
        search_pets_intent.training_phrases.extend(training_phrases)

        search_pets_intent.parameters.clear()
        search_pets_intent.parameters.extend(parameters)

        # Update the intent
        updated_intent = intents_client.update_intent(intent=search_pets_intent)

        logger.info(f"✓ Updated intent with {len(training_phrases)} training phrases")
        logger.info(f"✓ Added {len(parameters)} parameters (species, location, breed)")

        return True

    except Exception as e:
        logger.error(f"✗ Error updating intent: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Update Dialogflow CX intent with parameter annotations"
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
    logger.info("Updating Intent Parameters")
    logger.info("========================================")
    logger.info("")

    success = update_search_pets_intent(
        project_id=args.project_id,
        agent_id=args.agent_id,
        location=args.location
    )

    if success:
        logger.info("")
        logger.info("========================================")
        logger.info("✓ Intent Update Complete!")
        logger.info("========================================")
        logger.info("")
        logger.info("Now users can say things like:")
        logger.info("  'I want to adopt a dog in Seattle'")
        logger.info("  'Show me cats near Portland'")
        logger.info("And Dialogflow will extract the location and species automatically!")
        logger.info("")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("✗ Intent update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
