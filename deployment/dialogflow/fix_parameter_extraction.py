#!/usr/bin/env python3
"""
Complete Fix for Parameter Extraction in Dialogflow CX
This script:
1. Updates intent.search_pets with parameter annotations
2. Updates transition routes with parameter presets
3. Ensures location/species are extracted from initial utterance
"""

import sys
import subprocess
from loguru import logger


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix parameter extraction for PawConnect Dialogflow agent"
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
    logger.info("║  Parameter Extraction Fix              ║")
    logger.info("║  PawConnect Dialogflow CX              ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")
    logger.info(f"Project ID: {args.project_id}")
    logger.info(f"Agent ID: {args.agent_id}")
    logger.info(f"Location: {args.location}")
    logger.info(f"Webhook URL: {args.webhook_url or 'Not provided'}")
    logger.info("")

    # Step 1: Update intent with parameter annotations
    logger.info("========================================")
    logger.info("Step 1: Updating Intent Parameters")
    logger.info("========================================")
    logger.info("")

    try:
        cmd = [
            sys.executable,
            "deployment/dialogflow/update_intent_parameters.py",
            "--project-id", args.project_id,
            "--agent-id", args.agent_id,
            "--location", args.location
        ]

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)

        if result.returncode != 0:
            logger.error("✗ Failed to update intent parameters")
            if result.stderr:
                logger.error(result.stderr)
            return False

        logger.info("✓ Intent parameters updated successfully")

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to update intent parameters: {e}")
        if e.stdout:
            logger.error(e.stdout)
        if e.stderr:
            logger.error(e.stderr)
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False

    # Step 2: Update pages and flows with parameter presets
    logger.info("")
    logger.info("========================================")
    logger.info("Step 2: Updating Pages and Flows")
    logger.info("========================================")
    logger.info("")

    try:
        cmd = [
            sys.executable,
            "deployment/dialogflow/setup_complete_automation.py",
            "--project-id", args.project_id,
            "--agent-id", args.agent_id,
            "--location", args.location,
            "--skip-bash-setup"
        ]

        if args.webhook_url:
            cmd.extend(["--webhook-url", args.webhook_url])

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)

        if result.returncode != 0:
            logger.error("✗ Failed to update pages and flows")
            if result.stderr:
                logger.error(result.stderr)
            return False

        logger.info("✓ Pages and flows updated successfully")

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to update pages and flows: {e}")
        if e.stdout:
            logger.error(e.stdout)
        if e.stderr:
            logger.error(e.stderr)
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False

    # Success!
    logger.info("")
    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  ✓ Parameter Extraction Fixed!        ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info("")
    logger.info("✅ What was fixed:")
    logger.info("  • Intent training phrases now include parameter annotations")
    logger.info("  • Transition routes now have parameter presets")
    logger.info("  • Location and species are extracted from initial utterance")
    logger.info("")
    logger.info("📝 Test in Dialogflow Simulator:")
    logger.info("  Try: 'I want to adopt a dog in Seattle'")
    logger.info("  Expected: Agent extracts 'dog' and 'Seattle' automatically")
    logger.info("           No need to ask for location again!")
    logger.info("")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
