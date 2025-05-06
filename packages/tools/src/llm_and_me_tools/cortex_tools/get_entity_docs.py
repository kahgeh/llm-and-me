import sys
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

# Import shared constants and helpers
from llm_and_me_tools.cortex_tools.list_components import (
    CORTEX_API_BASE_URL,
    _get_cortex_auth_headers,
)

PRIVATE_COMPONENTS_OUTPUT_FILE = "cortex_team_components_private.json"
load_dotenv()


def get_cortex_entity_docs(
    tag_or_id: str, name: Optional[str] = None
) -> Dict[str, str]:
    """
    Retrieves OpenAPI documentation for a specific Cortex entity.

    Args:
        tag_or_id: The tag (x-cortex-tag) or unique ID of the entity.
        name: Optional name of the OpenAPI spec if multiple are configured.

    Returns:
        A dictionary containing the OpenAPI spec string, e.g., {"spec": "..."}.
        Returns an empty dictionary if the documentation is not found (404)
        or an error occurs.
    """
    headers = _get_cortex_auth_headers()
    api_url = f"{CORTEX_API_BASE_URL}/catalog/{tag_or_id}/documentation/openapi"
    params = {}
    if name:
        params["name"] = name

    print(
        f"Fetching OpenAPI docs for entity '{tag_or_id}'"
        f"{f' with name {name}' if name else ''}...",
        file=sys.stderr,
    )

    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)

        if response.status_code == 404:
            print(
                f"Documentation not found for entity '{tag_or_id}'"
                f"{f' with name {name}' if name else ''}.",
                file=sys.stderr,
            )
            return {}  # Return empty dict for not found

        response.raise_for_status()  # Raise HTTPError for other bad responses (4xx or 5xx)

        response_data = response.json()
        # Assuming the response structure is {"spec": "..."} based on docs
        if "spec" in response_data and isinstance(response_data["spec"], str):
            print(
                f"Successfully fetched documentation for '{tag_or_id}'.",
                file=sys.stderr,
            )
            return response_data
        else:
            print(
                f"Unexpected response format from Cortex API for '{tag_or_id}': {response_data}",
                file=sys.stderr,
            )
            return {}

    except requests.exceptions.RequestException as e:
        print(
            f"Error fetching documentation from Cortex API for '{tag_or_id}': {e}",
            file=sys.stderr,
        )
        return {}
    except Exception as e:
        print(
            f"An unexpected error occurred while fetching documentation for '{tag_or_id}': {e}",
            file=sys.stderr,
        )
        return {}


# Example usage for standalone testing (optional)
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_entity_docs.py <tag_or_id> [spec_name]")
        sys.exit(1)

    entity_tag_or_id = sys.argv[1]
    spec_name = sys.argv[2] if len(sys.argv) > 2 else None

    docs = get_cortex_entity_docs(entity_tag_or_id, spec_name)

    if docs:
        print("\n--- Documentation Spec ---")
        # Print the spec content or a confirmation
        print(docs.get("spec", "Spec content not found in response."))
        print("--------------------------")
    else:
        print("Failed to retrieve documentation.")
        sys.exit(1)
