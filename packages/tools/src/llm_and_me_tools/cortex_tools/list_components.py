import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# Constants
CORTEX_API_BASE_URL = "https://api.getcortexapp.com/api/v1"
PRIVATE_COMPONENTS_OUTPUT_FILE = "cortex_team_components_private.json"
load_dotenv()


class GitInfo(BaseModel):
    alias: Optional[str] = None
    basepath: Optional[str] = None
    provider: Optional[str] = None
    repository: Optional[str] = None
    repository_url: Optional[str] = Field(None, alias="repositoryUrl")


class HierarchyNode(BaseModel):
    description: Optional[str] = None
    groups: Optional[List[str]] = None
    id: Optional[str] = None
    name: Optional[str] = None
    # parents: Optional[Dict[str, Any]] = None # Simplified
    tag: Optional[str] = None
    tag: Optional[str] = None
    type: Optional[str] = None


# Define a simpler reference model to break recursion for schema generation
class HierarchyNodeRef(BaseModel):
    tag: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None


class Hierarchy(BaseModel):
    # Use List[Any] to definitively break schema recursion for Gemini
    children: Optional[List[Any]] = None
    parents: Optional[List[Any]] = None


class Link(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None


class MemberRole(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None


class MemberSource(BaseModel):
    external_group_id: Optional[str] = Field(None, alias="externalGroupId")
    external_id: Optional[str] = Field(None, alias="externalId")
    provider: Optional[str] = None
    type: Optional[str] = None


class Member(BaseModel):
    description: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[List[MemberRole]] = None
    sources: Optional[List[MemberSource]] = None


class MetadataItem(BaseModel):
    key: Optional[str] = None
    value: Optional[Any] = None  # Value can be complex


class OwnerIndividual(BaseModel):
    description: Optional[str] = None
    email: Optional[str] = None


class OwnerTeam(BaseModel):
    tag: str
    name: Optional[str] = None
    description: Optional[str] = None
    id: Optional[str] = None
    inheritance: Optional[str] = None
    is_archived: Optional[bool] = Field(None, alias="isArchived")
    provider: Optional[str] = None


class Owners(BaseModel):
    individuals: Optional[List[OwnerIndividual]] = None
    teams: Optional[List[OwnerTeam]] = None


class SlackChannel(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    notifications_enabled: Optional[bool] = Field(None, alias="notificationsEnabled")


class Entity(BaseModel):
    tag: str
    name: str
    type: str
    description: Optional[str] = None
    git: Optional[GitInfo] = None
    groups: Optional[List[str]] = None
    hierarchy: Optional[Hierarchy] = None
    id: Optional[str] = None
    is_archived: Optional[bool] = Field(None, alias="isArchived")
    last_updated: Optional[str] = Field(
        None, alias="lastUpdated"
    )  # Consider using datetime
    links: Optional[List[Link]] = None
    members: Optional[List[Member]] = None
    metadata: Optional[List[MetadataItem]] = None
    owners: Optional[Owners] = None  # Removed alias="ownersV2"
    slack_channels: Optional[List[SlackChannel]] = Field(None, alias="slackChannels")


class EntityListResponse(BaseModel):
    entities: List[Entity]
    page: int
    total: int
    total_pages: int = Field(alias="totalPages")


# --- Helper Functions ---


def _get_cortex_auth_headers() -> Dict[str, str]:
    """Retrieves Cortex API token from environment variables."""
    token = os.getenv("CORTEX_API_TOKEN")
    if not token:
        print(
            "Error: CORTEX_API_TOKEN environment variable not set.",
            file=sys.stderr,
        )
        sys.exit(1)  # Or raise an exception
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def load_components_data(
    file_path: str = PRIVATE_COMPONENTS_OUTPUT_FILE,
) -> List[Entity]:
    """Loads component data from the specified JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        # Validate and parse each entity dictionary into an Entity object
        return [Entity.model_validate(item) for item in data]
    except FileNotFoundError:
        print(f"Error: Components file not found at {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading components data: {e}", file=sys.stderr)
        sys.exit(1)


# --- Core Tool Functions ---


def list_cortex_components() -> List[Entity]:
    """
    Retrieves Cortex catalog entities of type 'service'.

    Returns:
        A list of Entity objects, each representing a service entity.
    """

    headers = _get_cortex_auth_headers()
    all_entities: List[Entity] = []
    page = 0
    page_size = 500  # Max page size seems to be 1000, but 500 is safer

    print("Fetching all components", file=sys.stderr)

    while True:
        params = {
            "types": ["service"],
            "pageSize": page_size,
            "page": page,
            "includeOwners": "true",
        }
        api_url = f"{CORTEX_API_BASE_URL}/catalog"

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            response_data = response.json()
            validated_response = EntityListResponse.model_validate(response_data)

            all_entities.extend(validated_response.entities)

            print(
                f"Page {page + 1}/{validated_response.total_pages}: Fetched {len(validated_response.entities)} entities.",
                file=sys.stderr,
            )

            if validated_response.page >= validated_response.total_pages - 1:
                break  # Exit loop if last page reached

            page += 1
            # TODO: Remove this break once pagination is confirmed working correctly
            # This break was added during debugging/testing pagination logic
            # break

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Cortex API: {e}", file=sys.stderr)
            # Decide how to handle: return partial data, raise exception, etc.
            # For now, return what we have gathered so far.
            break
        except ValidationError as e:
            print(f"Error validating Cortex API response: {e}", file=sys.stderr)
            print(
                f"Response JSON: {response.text[:500]}...", file=sys.stderr
            )  # Log part of the problematic response
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            break

    return all_entities


def save_cortex_components_private(
    components: List[Entity], output_file: str = PRIVATE_COMPONENTS_OUTPUT_FILE
) -> str:
    """Saves the fetched component data (list of Entity objects) to a JSON file."""
    try:
        # Convert Pydantic models to dictionaries for JSON serialization
        components_dict_list = [
            component.model_dump(exclude_none=True) for component in components
        ]
        with open(output_file, "w") as f:
            json.dump(components_dict_list, f, indent=2)
        print(f"Successfully saved components to {output_file}", file=sys.stderr)
        return output_file
    except IOError as e:
        print(f"Error writing to file {output_file}: {e}", file=sys.stderr)
        sys.exit(1)


# --- Main block for standalone execution ---
if __name__ == "__main__":
    print("Listing Cortex components...", file=sys.stderr)
    components = list_cortex_components()
    if components:
        output_filename = save_cortex_components_private(components)
        print(f"Components saved to {output_filename}", file=sys.stderr)
    else:
        print("No components fetched or an error occurred.", file=sys.stderr)
        sys.exit(1)
