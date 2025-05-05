#!/usr/bin/env python3
import json  # Added for saving data in private mode
import os
from typing import Any, List, Optional, Union  # Added Union for return type

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl

# Load environment variables from .env file
load_dotenv()


# Pydantic Models based on Cortex API response for GET /teams
class MemberRole(BaseModel):
    source: Optional[str] = None
    tag: Optional[str] = None
    type: Optional[str] = None


class Member(BaseModel):
    description: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    notifications_enabled: Optional[bool] = Field(None, alias="notificationsEnabled")
    role: Optional[MemberRole] = None
    roles: Optional[List[MemberRole]] = None


class CortexTeamDetails(BaseModel):
    members: Optional[List[Member]] = None


class Link(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[HttpUrl] = None


class Metadata(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    summary: Optional[str] = None


class SlackChannel(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    notifications_enabled: Optional[bool] = Field(None, alias="notificationsEnabled")


class Team(BaseModel):
    catalog_entity_tag: Optional[str] = Field(None, alias="catalogEntityTag")
    cortex_team: Optional[CortexTeamDetails] = Field(None, alias="cortexTeam")
    id: Optional[str] = None
    is_archived: Optional[bool] = Field(None, alias="isArchived")
    links: Optional[List[Link]] = None
    metadata: Optional[Metadata] = None
    slack_channels: Optional[List[SlackChannel]] = Field(None, alias="slackChannels")
    team_tag: Optional[str] = Field(None, alias="teamTag")
    type: Optional[str] = None


class TeamsResponse(BaseModel):
    teams: List[Team]


CORTEX_API_BASE_URL = "https://api.getcortexapp.com/api/v1"
PRIVATE_MODE_OUTPUT_FILE = "cortex_teams_private.json"


# Internal helper function for fetching and filtering
def _fetch_and_filter_cortex_teams(
    team_name_pattern: Optional[str] = None,
) -> Union[List[Team], str]:
    """
    Internal helper to fetch teams from Cortex API, validate, and filter.

    Requires the CORTEX_API_TOKEN environment variable to be set.
    Args:
        team_name_pattern: Optional regex pattern to filter teams by name.
    Returns:
        A list of Team objects matching the filter, or an error string.
    Raises:
        ValueError: If the CORTEX_API_TOKEN environment variable is not set.
        requests.exceptions.RequestException: If the API request fails.
    """
    api_token = os.getenv("CORTEX_API_TOKEN")
    if not api_token:
        raise ValueError("CORTEX_API_TOKEN environment variable not set.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }
    url = f"{CORTEX_API_BASE_URL}/teams"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

    # Parse the JSON response using the Pydantic model
    all_teams = TeamsResponse.model_validate(response.json()).teams
    filtered_teams = all_teams

    # Apply filtering if a pattern is provided
    if team_name_pattern:
        import re  # Import locally as it's only needed here

        try:
            # Filter teams where metadata.name exists and matches the pattern
            filtered_teams = [
                team
                for team in all_teams
                if team.metadata
                and team.metadata.name
                and re.search(team_name_pattern, team.metadata.name)
            ]
        except re.error as e:
            # Handle invalid regex patterns gracefully
            # Return the error string directly from the helper
            return f"Error: Invalid regex pattern provided: {e}"

    return filtered_teams


# --- Public Tool ---
def get_cortex_teams_public(
    team_name_pattern: Optional[str] = None,
) -> Union[List[Team], str]:
    """
    Retrieves and returns a list of teams from the Cortex API.

    Use this function when you want to display or process the team data directly.
    Requires the CORTEX_API_TOKEN environment variable to be set.

    Use this function only if you are not in private mode.

    Args:
        team_name_pattern: Optional regex pattern to filter teams by name.
    Returns:
        A list of Team objects matching the filter, or an error string if filtering failed.
    Raises:
        ValueError: If the CORTEX_API_TOKEN environment variable is not set.
        requests.exceptions.RequestException: If the API request fails.
    """
    # Calls the internal helper and returns its result directly
    return _fetch_and_filter_cortex_teams(team_name_pattern)


# --- Private Mode Tool ---
def save_cortex_teams_private(team_name_pattern: Optional[str] = None) -> str:
    """
    Retrieves teams from the Cortex API and saves them locally without returning data.

    Use this function in private mode to avoid exposing team data directly.
    Saves data to cortex_teams_private.json.
    Requires the CORTEX_API_TOKEN environment variable to be set.
    Args:
        team_name_pattern: Optional regex pattern to filter teams by name before saving.
    Returns:
        A string confirming success or describing an error.
    Raises:
        ValueError: If the CORTEX_API_TOKEN environment variable is not set.
        requests.exceptions.RequestException: If the API request fails.
    """
    result = _fetch_and_filter_cortex_teams(team_name_pattern)

    # Check if the helper returned an error string
    if isinstance(result, str):
        return result  # Propagate the error message

    # Proceed with saving if we received a list of teams
    filtered_teams = result
    try:
        # Convert Pydantic models to JSON serializable dictionaries
        teams_data = [team.model_dump(mode="json") for team in filtered_teams]
        with open(PRIVATE_MODE_OUTPUT_FILE, "w") as f:
            json.dump(teams_data, f, indent=2)
        print(
            f"Success: {len(filtered_teams)} team(s) data saved locally to {PRIVATE_MODE_OUTPUT_FILE}."
        )
        return PRIVATE_MODE_OUTPUT_FILE
    except IOError as e:
        return f"Error: Failed to save data locally in private mode: {e}"
    except Exception as e:  # Catch potential model_dump errors
        return f"Error: Failed processing data for local saving: {e}"


if __name__ == "__main__":
    try:
        private_result = save_cortex_teams_private()
        print(private_result)  # Prints the success/error message
    except (ValueError, requests.exceptions.RequestException) as e:
        print(f"Error: {e}")
    except Exception as e:  # Catch potential Pydantic validation errors too
        print(f"An unexpected error occurred: {e}")
