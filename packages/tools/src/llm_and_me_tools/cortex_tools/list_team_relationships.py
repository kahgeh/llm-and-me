import json
import os
import sys
from typing import List, Literal, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# --- Constants ---
CORTEX_API_BASE_URL = "https://api.getcortexapp.com/api/v1"
PRIVATE_RELATIONSHIPS_OUTPUT_FILE = "cortex_team_relationships_private.json"
load_dotenv()


# --- Pydantic Models ---
# Note: We are not defining the full Team model here from list_teams.py,
# just using dicts after loading from JSON for simplicity in this module.
# Note: We are not defining the full Team model here from list_teams.py,
# just using dicts after loading from JSON for simplicity in this module.
class Edge(BaseModel):
    child_team_tag: str = Field(..., alias="childTeamTag")
    parent_team_tag: str = Field(..., alias="parentTeamTag")
    provider: Optional[Literal["WORKDAY"]] = None


class TeamRelationshipsResponse(BaseModel):
    edges: List[Edge]


# --- Helper Function ---
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


def load_relationships_data(
    file_path: str = PRIVATE_RELATIONSHIPS_OUTPUT_FILE,
) -> List[Edge]:
    """Loads team relationships data from the specified JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            relationships_data = json.load(f)
            if isinstance(relationships_data, list):
                # Validate and parse each edge dictionary into an Edge object
                edges = [
                    Edge.model_validate(edge_data) for edge_data in relationships_data
                ]
                return edges
            else:
                print(
                    f"Error: Expected a list in {file_path}, got {type(relationships_data)}",
                    file=sys.stderr,
                )
                return []
    except FileNotFoundError:
        print(f"Error: Relationships file not found at {file_path}", file=sys.stderr)
        print(
            f"Hint: Ensure '{file_path}' exists. You might need to run 'get_team_relationships.py' first.",
            file=sys.stderr,
        )
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}", file=sys.stderr)
        return []
    except IOError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:  # Catch potential Pydantic validation errors too
        print(
            f"Error processing relationships data from {file_path}: {e}",
            file=sys.stderr,
        )
        return []


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


def save_cortex_team_relationships_private(
    output_file: str = PRIVATE_RELATIONSHIPS_OUTPUT_FILE,
) -> str:
    """
    Fetches Cortex team relationships and saves them to a JSON file.

    Args:
        output_file: The path to the file where the relationships should be saved.
                     Defaults to PRIVATE_RELATIONSHIPS_OUTPUT_FILE.

    Returns:
        The path to the saved file if successful, otherwise an empty string.
    """
    relationships = get_cortex_team_relationships()
    if not relationships:
        print("No relationships fetched, cannot save to file.", file=sys.stderr)
        return ""

    try:
        # Convert Pydantic models to a list of dictionaries for JSON serialization
        relationships_dict = [edge.model_dump(by_alias=True) for edge in relationships]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(relationships_dict, f, indent=2)
        print(f"Successfully saved {len(relationships)} relationships to {output_file}")
        return output_file
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"An unexpected error occurred during saving: {e}", file=sys.stderr)
        return ""


# --- Main execution for testing ---
if __name__ == "__main__":
    print("\nAttempting to save Cortex team relationships...")
    saved_file_path = save_cortex_team_relationships_private()

    if saved_file_path:
        print(f"Relationships saved to: {saved_file_path}")
    else:
        print("Failed to save relationships.")
