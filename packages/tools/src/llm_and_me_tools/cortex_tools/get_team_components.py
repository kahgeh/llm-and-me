import os
import sys
from typing import List, Set

# Assuming these sibling modules exist and contain the necessary functions/constants
from llm_and_me_tools.cortex_tools.get_descendent_teams import get_descendant_teams
from llm_and_me_tools.cortex_tools.list_components import (
    PRIVATE_COMPONENTS_OUTPUT_FILE,
    Entity,
    load_components_data,
)
from llm_and_me_tools.cortex_tools.list_team_relationships import (
    PRIVATE_RELATIONSHIPS_OUTPUT_FILE,
    load_relationships_data,
)
from llm_and_me_tools.cortex_tools.list_teams import (
    PRIVATE_MODE_OUTPUT_FILE as PRIVATE_TEAMS_OUTPUT_FILE,
)
from llm_and_me_tools.cortex_tools.list_teams import (
    create_tag_to_team_map,
    load_teams_data,
)


def get_team_components(top_level_team_tag: str) -> List[Entity]:
    """
    Loads teams, relationships, and components from JSON files,
    finds all descendant teams of the given top-level team,
    and returns components owned by any of these teams.

    Args:
        top_level_team_tag: The tag of the top-level team.

    Returns:
        A list of Entity objects representing the components owned by the
        top-level team and its descendants.
    """
    # 1. Load data
    print(f"Loading teams data from {PRIVATE_TEAMS_OUTPUT_FILE}...", file=sys.stderr)
    teams_data = load_teams_data(PRIVATE_TEAMS_OUTPUT_FILE)
    print(
        f"Loading relationships data from {PRIVATE_RELATIONSHIPS_OUTPUT_FILE}...",
        file=sys.stderr,
    )
    relationships_data = load_relationships_data(PRIVATE_RELATIONSHIPS_OUTPUT_FILE)
    print(
        f"Loading components data from {PRIVATE_COMPONENTS_OUTPUT_FILE}...",
        file=sys.stderr,
    )
    # Load components using the imported function
    all_components = load_components_data(PRIVATE_COMPONENTS_OUTPUT_FILE)

    # 2. Prepare team map and find descendants
    print("Creating team map...", file=sys.stderr)
    tag_to_team_map = create_tag_to_team_map(teams_data)

    if top_level_team_tag not in tag_to_team_map:
        print(
            f"Error: Top-level team tag '{top_level_team_tag}' not found in teams data.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Finding descendant teams for '{top_level_team_tag}'...", file=sys.stderr)
    descendant_teams = get_descendant_teams(
        top_level_team_tag, relationships_data, tag_to_team_map
    )

    # Include the top-level team itself in the set of relevant teams
    # Use team_tag attribute from the Team model in get_descendent_teams.py
    relevant_team_tags: Set[str] = {team.team_tag for team in descendant_teams}
    relevant_team_tags.add(top_level_team_tag)
    print(
        f"Found {len(relevant_team_tags)} relevant teams (including descendants and self).",
        file=sys.stderr,
    )

    # 3. Filter components
    print("Filtering components by ownership...", file=sys.stderr)
    team_components: List[Entity] = []
    for component in all_components:
        if component.owners and component.owners.teams:
            component_owner_tags = {
                owner.tag for owner in component.owners.teams if owner.tag
            }
            # Check if any of the component's owner teams are in the relevant set
            if not component_owner_tags.isdisjoint(relevant_team_tags):
                team_components.append(component)

    print(
        f"Found {len(team_components)} components owned by '{top_level_team_tag}' or its descendants.",
        file=sys.stderr,
    )
    return team_components


# Note: The main block and list/save functions were moved to list_components.py


# --- Main block for standalone execution ---
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Get Cortex components owned by a team and its descendants."
    )
    parser.add_argument(
        "top_level_team_tag",
        help="The tag of the top-level team to query.",
    )
    parser.add_argument(
        "--json",
        default=False,
        action="store_true",
        help="Output as JSON.Suppress all other output.",
    )
    args = parser.parse_args()

    if args.json:
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")

    print(
        f"Getting components for team '{args.top_level_team_tag}' and its descendants...",
        file=sys.stderr,
    )
    components = get_team_components(args.top_level_team_tag)

    if components:
        # Convert Pydantic models to dictionaries for JSON output
        components_dict_list = [
            component.model_dump(exclude_none=True) for component in components
        ]
        # Restore stdout
        if args.json:
            sys.stdout.close()
            sys.stdout = original_stdout

        print(json.dumps(components_dict_list, indent=2))
        if args.json:
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, "w")

        print(
            f"\nSuccessfully retrieved {len(components)} components.", file=sys.stderr
        )
    else:
        print(
            f"No components found for team '{args.top_level_team_tag}' or its descendants.",
            file=sys.stderr,
        )

    # Restore stdout
    if args.json:
        sys.stdout.close()
        sys.stdout = original_stdout
