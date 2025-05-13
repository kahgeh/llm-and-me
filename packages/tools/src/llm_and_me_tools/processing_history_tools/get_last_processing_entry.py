import argparse
import datetime
import sys
from typing import Optional

from pydantic import BaseModel


class ProcessingHistoryEntry(BaseModel):
    """
    Represents a single entry in the processing history.
    """

    entity_id: str
    processing_type: str
    key: str
    value: str
    timestamp: datetime.datetime


def get_last_processing_entry(
    entity_id: str, processing_type: str, key: str
) -> Optional[ProcessingHistoryEntry]:
    """
    Retrieves the last processing history entry for a given entity,
    processing type, and key.

    This function currently returns None as a placeholder.
    Actual data retrieval from a persistent store (e.g., SQLite database)
    needs to be implemented. The store should be designed to "keep only the last"
    record for a given combination of entity_id, processing_type, and key,
    or this function should ensure it fetches only the most recent one.

    Args:
        entity_id: The unique identifier of the entity.
        processing_type: The category or type of processing performed.
        key: The specific aspect or metric being recorded.

    Returns:
        A ProcessingHistoryEntry object if a record is found, otherwise None.
    """
    # TODO: Implement interaction with a persistent data store (e.g., SQLite)
    # to fetch the actual last processing entry.
    # For example:
    # if entity_id == "example_entity" and processing_type == "validation" and key == "check1":
    #     return ProcessingHistoryEntry(
    #         entity_id=entity_id,
    #         processing_type=processing_type,
    #         key=key,
    #         value="SUCCESS",
    #         timestamp=datetime.datetime.now(datetime.timezone.utc)
    #     )
    return None


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Get the last processing history entry for an entity."
    )
    parser.add_argument("entity_id", help="The ID of the entity.")
    parser.add_argument("processing_type", help="The type of processing.")
    parser.add_argument("key", help="The key for the processing status.")
    return parser.parse_args()


def main_cli():
    """Main function for the command-line interface."""
    args = parse_args()
    entry = get_last_processing_entry(
        args.entity_id, args.processing_type, args.key
    )
    if entry:
        # Output as JSON for easy parsing if needed, or human-readable format
        print(entry.model_dump_json(indent=2))
    else:
        print(
            f"No processing history entry found for entity_id='{args.entity_id}', "
            f"processing_type='{args.processing_type}', key='{args.key}'.",
            file=sys.stderr,
        )
        # Exit with a non-zero status code if no entry is found,
        # which can be useful for scripting.
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
