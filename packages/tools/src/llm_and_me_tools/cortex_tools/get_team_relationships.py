import os
import sys
from typing import List, Literal, Optional

import requests
from pydantic import BaseModel, Field, ValidationError


# --- Constants ---
CORTEX_API_BASE_URL = "https://api.getcortexapp.com/api/v1"


# --- Pydantic Models ---
class Edge(BaseModel):
    child_team_tag: str = Field(..., alias="childTeamTag")
    parent_team_tag: str = Field(..., alias="parentTeamTag")
    provider: Optional[Literal["WORKDAY"]] = None


class TeamRelationshipsResponse(BaseModel):
    edges: List[Edge]


# --- Helper Functions ---
def _get_cortex_auth_headers() -> dict:
    """Retrieves Cortex API authentication headers."""
    api_token = os.getenv("CORTEX_API_TOKEN")
    if not api_token:
        print(
            "Error: CORTEX_API_TOKEN environment variable not set.",
            file=sys.stderr,
        )
        sys.exit(1)  # Or raise an exception
    return {"Authorization": f"Bearer {api_token}"}


# --- Tool Function ---
def get_cortex_team_relationships() -> List[Edge]:
    """
    Retrieves team relationships (hierarchies) from the Cortex API.

    Returns:
        A list of Edge objects representing the parent-child relationships
        between teams.
    """
    headers = _get_cortex_auth_headers()
    url = f"{CORTEX_API_BASE_URL}/teams/relationships"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()
        validated_data = TeamRelationshipsResponse.model_validate(response_data)
        return validated_data.edges

    except requests.exceptions.RequestException as e:
        print(f"Error during Cortex API request: {e}", file=sys.stderr)
        # Depending on desired behavior, could return empty list or raise
        return []
    except ValidationError as e:
        print(f"Error validating Cortex API response: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return []


# --- Main execution for testing ---
if __name__ == "__main__":
    print("Attempting to fetch Cortex team relationships...")
    relationships = get_cortex_team_relationships()
    if relationships:
        print(f"Successfully fetched {len(relationships)} relationships:")
        for edge in relationships:
            print(
                f"- Child: {edge.child_team_tag}, Parent: {edge.parent_team_tag}"
            )
    else:
        print("Failed to fetch relationships or none found.")
