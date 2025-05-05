import argparse
import json
import sys
from typing import Dict, List, Set

from pydantic import BaseModel, Field

from llm_and_me_tools.cortex_tools.get_team_relationships import (
    PRIVATE_RELATIONSHIPS_OUTPUT_FILE,
    Edge,
)
from llm_and_me_tools.cortex_tools.list_teams import PRIVATE_MODE_OUTPUT_FILE

# Pydantic v2: Use model_config dictionary
# Pydantic v1: Use Config class
# Ensure population by field name is allowed when aliases are present
# Make the model immutable (hashable) so it can be added to sets
TeamConfig = {"populate_by_name": True, "extra": "ignore", "frozen": True}


class Team(BaseModel):
    model_config = TeamConfig
    id: str = Field(..., alias="teamId")
    team_tag: str = Field(..., alias="teamTag")
    parent_team_tag: str = Field(..., alias="parentTeamTag")
    team_name: str = Field(..., alias="name")


class _Team(BaseModel):
    id: str = Field(..., alias="teamId")
    name: str = Field(..., alias="name")


# --- Helper Functions ---
def _load_teams_data(file_path: str = PRIVATE_MODE_OUTPUT_FILE) -> List[dict]:
    """Loads team data from the specified JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            teams_data = json.load(f)
            if isinstance(teams_data, list):
                return teams_data
            else:
                print(
                    f"Error: Expected a list in {file_path}, got {type(teams_data)}",
                    file=sys.stderr,
                )
                return []
    except FileNotFoundError:
        print(f"Error: Teams file not found at {file_path}", file=sys.stderr)
        print(
            f"Hint: Ensure '{file_path}' exists. You might need to run the script that generates it.",
            file=sys.stderr,
        )
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}", file=sys.stderr)
        return []
    except IOError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return []


def _load_relationships_data(
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


def _create_tag_to_team_map(teams_data: List[dict]) -> Dict[str, _Team]:
    """Creates a mapping from team tag to team name."""
    tag_to_team_map = {}
    for team in teams_data:
        tag = team.get("team_tag")  # Corresponds to Team.team_tag
        id = team.get("id")
        metadata = team.get("metadata")
        name = (
            metadata.get("name") if isinstance(metadata, dict) else None
        )  # Corresponds to Metadata.name

        if tag and name and id:
            tag_to_team_map[tag] = _Team(teamId=id, name=name)
        elif tag:
            print(
                f"Warning: Missing 'name' in metadata for team tag '{tag}'.",
                file=sys.stderr,
            )
        # else: # Don't warn if tag itself is missing, less critical here
        # print(f"Warning: Missing 'team_tag' in team data entry: {team}", file=sys.stderr)
    return tag_to_team_map


# --- Tool Function ---
def get_descendant_teams(
    top_level_team_tag: str,
    all_relationships: List[Edge],
    tag_to_team_map: Dict[str, _Team],
) -> List[Team]:
    """
    Finds all descendant team names for a given top-level team tag.

    Requires a pre-built map of team tags to team names.

    Args:
        top_level_team_tag: The tag of the team to start the traversal from.
        all_relationships: A list of all Edge objects representing team relationships.
        tag_to_name_map: A dictionary mapping team tags to team names.

    Returns:
        A sorted list of team names that are descendants of the top_level_team_tag.
        If a name is not found for a tag, the tag itself is used as a fallback.
    """
    # Build an adjacency list (parent -> list of children) for efficient lookup
    adj: Dict[str, List[str]] = {}
    for edge in all_relationships:
        if edge.parent_team_tag not in adj:
            adj[edge.parent_team_tag] = []
        adj[edge.parent_team_tag].append(edge.child_team_tag)

    descendents: Set[Team] = set()
    queue: List[str] = [top_level_team_tag]  # Use a queue for BFS

    processed_teams: Set[str] = set()  # Keep track of teams already processed

    while queue:
        current_team = queue.pop(0)
        # Skip if already processed (handles cycles)
        if current_team in processed_teams:
            continue
        processed_teams.add(current_team)

        # Check if the current team has children
        if current_team in adj:
            for child_team in adj[current_team]:
                # Process child only if it hasn't been processed yet
                if child_team not in processed_teams:
                    # Get the name of the CHILD team
                    _team = tag_to_team_map.get(child_team)
                    child_name = _team.name
                    id = _team.id
                    if child_name is None:
                        # Use tag as fallback if name not found
                        print(
                            f"Warning: Name not found for descendant team tag '{child_team}'. Using tag.",
                            file=sys.stderr,
                        )
                        child_name = child_team

                    # Create the Team object using FIELD NAMES
                    descendant_team_obj = Team(
                        id=id,
                        team_tag=child_team,
                        parent_team_tag=current_team,
                        team_name=child_name,  # Use the fetched/fallback child name
                    )

                    # Add the descendant team object to the set
                    descendents.add(descendant_team_obj)

                    # Add the child team tag to the queue for further traversal
                    # Important: Add to queue *after* adding to descendents and *only if* not processed
                    # The check `if child_team not in processed_teams:` ensures we don't re-add to queue
                    queue.append(child_team)

    # Convert the set to a sorted list before returning
    # Sort by team_tag for consistent output
    return sorted(list(descendents), key=lambda team: team.team_tag)


# --- Main execution ---
def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Find descendant teams for a given Cortex team tag based on pre-generated data files."
    )
    parser.add_argument(
        "--team-tag",
        required=True,
        help="The tag of the top-level team to find descendants for.",
    )
    parser.add_argument(
        "--teams-file",
        default=PRIVATE_MODE_OUTPUT_FILE,
        help=f"Path to the JSON file containing team details (default: {PRIVATE_MODE_OUTPUT_FILE}).",
    )
    parser.add_argument(
        "--relationships-file",
        default=PRIVATE_RELATIONSHIPS_OUTPUT_FILE,
        help=f"Path to the JSON file containing team relationships (default: {PRIVATE_RELATIONSHIPS_OUTPUT_FILE}).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print(f"Loading team data from: {args.teams_file}")
    teams_data = _load_teams_data(args.teams_file)
    if not teams_data:
        sys.exit(1)

    print(f"Loading relationship data from: {args.relationships_file}")
    relationships = _load_relationships_data(args.relationships_file)
    if not relationships:
        sys.exit(1)

    print("Creating team tag to team map...")
    tag_map = _create_tag_to_team_map(teams_data)
    if not tag_map:
        print(
            "Warning: Team tag map is empty. Names might not be resolved.",
            file=sys.stderr,
        )
        # Continue execution, but names will likely be tags

    print(f"\nFinding descendants for team tag: {args.team_tag}")
    descendant_teams_list = get_descendant_teams(args.team_tag, relationships, tag_map)

    if descendant_teams_list:
        print("\nDescendant Teams (Child Tag : Parent Tag : Team Name):")
        # The function now returns a sorted list of Team objects
        for team in descendant_teams_list:
            print(
                f"- {team.id} {team.team_tag} (Parent: {team.parent_team_tag}) : {team.team_name}"
            )
    else:
        print(f"No descendants found for team tag '{args.team_tag}'.")
