#!/usr/bin/env python3
"""
Complete Dialogflow CX Setup Automation for PawConnect
Combines entity types, intents, pages, flows, and webhooks setup.
"""

import os
import sys
import subprocess
import argparse
from typing import Optional
from loguru import logger

# Import our custom automation
from setup_dialogflow_automation import DialogflowAutomation


class DialogflowCompleteSetup:
    """Complete automated setup for Dialogflow CX agent."""

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        location: str = "us-central1",
        webhook_url: Optional[str] = None,
        skip_bash_setup: bool = False
    ):
        """
        Initialize complete setup automation.

        Args:
            project_id: GCP project ID
            agent_id: Dialogflow CX agent ID
            location: Agent location
            webhook_url: Webhook URL for fulfillments
            skip_bash_setup: Skip bash script for intents/entities if already created
        """
        self.project_id = project_id
        self.agent_id = agent_id
        self.location = location
        self.webhook_url = webhook_url
        self.skip_bash_setup = skip_bash_setup

        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.bash_script_path = os.path.join(self.script_dir, "setup-agent.sh")

    def run_bash_setup(self) -> bool:
        """
        Run the bash script to create entity types and intents.

        Returns:
            True if successful, False otherwise
        """
        logger.info("========================================")
        logger.info("Step 1: Creating Entity Types & Intents")
        logger.info("========================================")

        if self.skip_bash_setup:
            logger.info("⚠ Skipping bash setup (--skip-bash-setup flag)")
            return True

        if not os.path.exists(self.bash_script_path):
            logger.error(f"✗ Bash script not found: {self.bash_script_path}")
            return False

        # Check if running on Windows
        if sys.platform == "win32":
            logger.warning(
                "⚠ Detected Windows platform. The bash script requires WSL, Git Bash, or similar."
            )
            logger.info("Options if Entity Types & Intents are not created:")
            logger.info("1. Run the setup-agent.sh script manually in WSL/Git Bash")
            logger.info("2. Use --skip-bash-setup if intents/entities are already created")
            logger.info("3. Continue with Python-only setup (pages and flows)")

            response = input("\nContinue with Python-only setup? (y/N): ")
            if response.lower() != 'y':
                logger.info("Setup cancelled by user")
                return False

            logger.info("Continuing with Python-only setup...")
            return True

        # Run bash script
        try:
            cmd = [
                "bash",
                self.bash_script_path,
                self.agent_id,
                self.location,
                self.project_id
            ]

            logger.info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            logger.info(result.stdout)
            if result.stderr:
                logger.warning(result.stderr)

            logger.info("✓ Entity types and intents created successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Bash script failed: {e}")
            if e.stdout:
                logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"stderr: {e.stderr}")
            return False

        except Exception as e:
            logger.error(f"✗ Error running bash script: {e}")
            return False

    def run_python_setup(self) -> bool:
        """
        Run the Python automation to create pages, flows, and webhooks.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n========================================")
        logger.info("Step 2: Creating Pages, Flows & Webhooks")
        logger.info("========================================")

        automation = DialogflowAutomation(
            project_id=self.project_id,
            agent_id=self.agent_id,
            location=self.location,
            webhook_url=self.webhook_url
        )

        return automation.setup_pawconnect_agent()

    def run_complete_setup(self) -> bool:
        """
        Run complete setup including both bash and Python automation.

        Returns:
            True if successful, False otherwise
        """
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║  PawConnect Dialogflow CX Automation   ║")
        logger.info("║         Complete Setup Script          ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("")
        logger.info(f"Project ID: {self.project_id}")
        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"Location: {self.location}")
        logger.info(f"Webhook URL: {self.webhook_url or 'Not provided'}")
        logger.info("")

        # Step 1: Bash setup (entity types and intents)
        if not self.run_bash_setup():
            logger.error("\n✗ Setup failed during entity types/intents creation")
            return False

        # Step 2: Python setup (pages, flows, webhooks)
        if not self.run_python_setup():
            logger.error("\n✗ Setup failed during pages/flows/webhooks creation")
            return False

        # Success!
        logger.info("\n╔════════════════════════════════════════╗")
        logger.info("║  ✓ Complete Setup Successful!          ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info("\n📋 What was configured:")
        logger.info("  • Entity Types (if bash setup was run)")
        logger.info("  • Intents (if bash setup was run)")
        logger.info("  • Webhook (PawConnect Webhook)")
        logger.info("  • Pages (Pet Search, Pet Details, Get Recommendations, Schedule Visit, etc.)")
        logger.info("  • Transition Routes (auto-created if intents exist)")
        logger.info("  • Flow Event Handlers (welcome message)")
        logger.info("\n🔧 Next steps:")
        logger.info("  1. Test your agent in the Dialogflow CX Simulator")
        logger.info("  2. Verify transition routes were created correctly")
        logger.info("  3. Fine-tune parameters, fulfillments, and welcome message as needed")
        logger.info("  4. If intents/entity types are missing, run the bash setup script")
        logger.info("\n📚 For more information:")
        logger.info("  - See deployment/dialogflow/README.md")
        logger.info("  - See docs/DEPLOYMENT.md")
        logger.info("  - See docs/DIALOG_FLOW_COMPLETE_SETUP.md")
        logger.info("")

        return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Complete automated setup for PawConnect Dialogflow CX agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full setup with webhook URL
  python setup_complete_automation.py \\
    --project-id my-project \\
    --agent-id abc123 \\
    --webhook-url https://my-app.run.app/webhook

  # Setup without webhook (add webhook URL later in Console)
  python setup_complete_automation.py \\
    --project-id my-project \\
    --agent-id abc123

  # Skip bash script if intents/entities already exist
  python setup_complete_automation.py \\
    --project-id my-project \\
    --agent-id abc123 \\
    --skip-bash-setup

Environment Variables:
  GOOGLE_APPLICATION_CREDENTIALS: Path to service account key JSON
  GOOGLE_CLOUD_PROJECT: GCP project ID (alternative to --project-id)
        """
    )

    parser.add_argument(
        "--project-id",
        help="GCP project ID (or set GOOGLE_CLOUD_PROJECT env var)"
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Dialogflow CX agent ID (get from Dialogflow Console or API)"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Agent location (default: us-central1)"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL for fulfillments (e.g., https://your-app.run.app/webhook)"
    )
    parser.add_argument(
        "--skip-bash-setup",
        action="store_true",
        help="Skip bash script setup (use if intents/entities already created)"
    )

    args = parser.parse_args()

    # Get project ID from args or environment
    project_id = args.project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("✗ Project ID required: use --project-id or set GOOGLE_CLOUD_PROJECT")
        sys.exit(1)

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="INFO"
    )

    # Verify authentication
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning(
            "⚠ GOOGLE_APPLICATION_CREDENTIALS not set. "
            "Ensure you have authenticated with gcloud auth application-default login"
        )

    # Run complete setup
    setup = DialogflowCompleteSetup(
        project_id=project_id,
        agent_id=args.agent_id,
        location=args.location,
        webhook_url=args.webhook_url,
        skip_bash_setup=args.skip_bash_setup
    )

    success = setup.run_complete_setup()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
