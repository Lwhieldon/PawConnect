#!/usr/bin/env python3
"""List all Dialogflow CX agents in the project."""

import sys
from google.cloud.dialogflowcx_v3 import AgentsClient
from google.api_core.client_options import ClientOptions


def list_agents(project_id: str, location: str = "us-central1"):
    """List all agents in the project."""
    try:
        # Build parent path
        parent = f"projects/{project_id}/locations/{location}"

        # Build regional API endpoint
        api_endpoint = f"{location}-dialogflow.googleapis.com"
        client_options = ClientOptions(api_endpoint=api_endpoint)

        # Initialize client
        agents_client = AgentsClient(client_options=client_options)

        print(f"Listing agents in: {parent}")
        print("=" * 80)
        print()

        # List agents
        agents = list(agents_client.list_agents(parent=parent))

        if not agents:
            print("No agents found in this project/location.")
            return

        for agent in agents:
            # Extract agent ID from full path
            # Format: projects/PROJECT/locations/LOCATION/agents/AGENT_ID
            agent_id = agent.name.split("/")[-1]

            print(f"Agent: {agent.display_name}")
            print(f"  Full Name: {agent.name}")
            print(f"  Agent ID: {agent_id}")
            print(f"  Default Language: {agent.default_language_code}")
            print(f"  Time Zone: {agent.time_zone}")
            print()

        print("=" * 80)
        print(f"Total agents found: {len(agents)}")

    except Exception as e:
        print(f"Error listing agents: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="List Dialogflow CX agents")
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Location (default: us-central1)"
    )

    args = parser.parse_args()
    list_agents(args.project_id, args.location)
