import argparse
import json
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

NEW_RELIC_API_KEY_ENV_VAR = "NEW_RELIC_API_KEY"
NERDGRAPH_API_URL = "https://api.newrelic.com/graphql"
load_dotenv()


class NerdGraphApiEntity(BaseModel):
    guid: str
    name: str
    domain: str
    type: str
    entity_type: str = Field(..., alias="entityType")


class NerdGraphApiResults(BaseModel):
    entities: List[NerdGraphApiEntity]


class NerdGraphApiEntitySearch(BaseModel):
    results: NerdGraphApiResults


class NerdGraphApiActor(BaseModel):
    entity_search: NerdGraphApiEntitySearch = Field(..., alias="entitySearch")


class NerdGraphApiResponse(BaseModel):
    actor: NerdGraphApiActor


class NerdGraphApiData(BaseModel):
    data: NerdGraphApiResponse
    errors: Optional[List[dict]] = None


class ApmEntity(BaseModel):
    guid: str
    name: str
    domain: str
    type: str
    entity_type: str


def _get_new_relic_api_key() -> str:
    api_key = os.getenv(NEW_RELIC_API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(
            f"Environment variable {NEW_RELIC_API_KEY_ENV_VAR} is not set."
        )
    return api_key


def get_prod_apm_entities_by_component_tag(component_tag: str) -> Optional[ApmEntity]:
    """Fetches New Relic APM application entity details by component tag UUID.

    Queries the NerdGraph API for APM application entities matching the given
    component_tag (uuid). If multiple entities are found, it attempts to return
    one with 'live', 'prod', or 'production' in its name. Otherwise, it returns
    the first entity found.

    Requires the NEW_RELIC_API_KEY environment variable to be set.

    Args:
        component_tag: The component tag UUID to search for.

    Returns:
        An ApmEntity object if a matching entity is found, otherwise None.
    """
    api_key = _get_new_relic_api_key()
    headers = {
        "API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    query = f"""
    {{
      actor {{
        entitySearch(query: "tags.uuid = '{component_tag}' AND type = 'APPLICATION' AND domain = 'APM'") {{
          results {{
            entities {{
              guid
              name
              domain
              type
              entityType
            }}
          }}
        }}
      }}
    }}
    """

    response = requests.post(NERDGRAPH_API_URL, headers=headers, json={"query": query})
    response.raise_for_status()

    response_json = response.json()

    if "errors" in response_json and response_json["errors"]:
        raise ValueError(f"NerdGraph API returned errors: {response_json['errors']}")

    parsed_response = NerdGraphApiData(**response_json)

    if (
        not parsed_response.data
        or not parsed_response.data.actor
        or not parsed_response.data.actor.entity_search
        or not parsed_response.data.actor.entity_search.results
        or not parsed_response.data.actor.entity_search.results.entities # Ensure entities list itself is not None
    ):
        return None

    api_entities = parsed_response.data.actor.entity_search.results.entities
    if not api_entities: # Explicit check for empty list
        return None

    output_entities = [
        ApmEntity(
            guid=entity.guid,
            name=entity.name,
            domain=entity.domain,
            type=entity.type,
            entity_type=entity.entity_type,
        )
        for entity in api_entities
    ]

    if len(output_entities) == 1:
        return output_entities[0]

    # len(output_entities) > 1 case
    preferred_keywords = ["live", "prod", "production"]
    for entity in output_entities:
        entity_name_lower = entity.name.lower()
        for keyword in preferred_keywords:
            if keyword in entity_name_lower:
                return entity  # Return the preferred entity

    # If multiple entities and none match preferred keywords, return the first one.
    return output_entities[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Get APM entities by component tag from New Relic."
    )
    parser.add_argument("--component-tag", help="The component tag to search for.")
    return parser.parse_args()


def main_cli():
    args = parse_args()
    try:
        entity = get_prod_apm_entities_by_component_tag(args.component_tag)
        if entity:
            print(json.dumps(entity.model_dump(), indent=2))
        else:
            print(json.dumps(None)) # Or print a message like "No entity found."
    except ValueError as e:
        # Specific errors from the function (API key, NerdGraph errors)
        print(f"Error: {e}")
        exit(1)
    except requests.exceptions.RequestException as e:
        # Errors from the HTTP request itself
        print(f"Request Error: {e}")
        exit(1)
    except Exception as e:
        # Catch-all for any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main_cli()
