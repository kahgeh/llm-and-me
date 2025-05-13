import argparse
import datetime
import sqlite3
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
    db_file: str, entity_id: str, processing_type: str, key: str
) -> Optional[ProcessingHistoryEntry]:
    """
    Retrieves the last processing history entry for a given entity,
    processing type, and key from an SQLite database.

    Args:
        db_file: Path to the SQLite database file.
        entity_id: The unique identifier of the entity.
        processing_type: The category or type of processing performed.
        key: The specific aspect or metric being recorded.

    Returns:
        A ProcessingHistoryEntry object if a record is found, otherwise None.
    """
    try:
        with sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
            # Ensure the table exists, though this function primarily reads.
            # This matches the save_processing_entry.py behavior of creating if not exists.
            # In a real scenario, table creation might be handled separately or guaranteed.
            cursor_create = conn.cursor()
            cursor_create.execute(
                """
                CREATE TABLE IF NOT EXISTS processing_history (
                    entity_id TEXT NOT NULL,
                    processing_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (entity_id, processing_type, key)
                )
                """
            )
            conn.commit()

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT entity_id, processing_type, key, value, timestamp
                FROM processing_history
                WHERE entity_id = ? AND processing_type = ? AND key = ?
                """,
                (entity_id, processing_type, key),
            )
            row = cursor.fetchone()

            if row:
                return ProcessingHistoryEntry(
                    entity_id=row[0],
                    processing_type=row[1],
                    key=row[2],
                    value=row[3],
                    timestamp=datetime.datetime.fromisoformat(row[4]),
                )
    except sqlite3.Error as e:
        print(f"SQLite error: {e}", file=sys.stderr)
        # Depending on desired behavior, you might re-raise or handle differently
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None
    return None


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Get the last processing history entry for an entity from an SQLite database."
    )
    parser.add_argument("db_file", help="Path to the SQLite database file.")
    parser.add_argument("entity_id", help="The ID of the entity.")
    parser.add_argument("processing_type", help="The type of processing.")
    parser.add_argument("key", help="The key for the processing status.")
    return parser.parse_args()


def main_cli():
    """Main function for the command-line interface."""
    args = parse_args()
    entry = get_last_processing_entry(
        args.db_file, args.entity_id, args.processing_type, args.key
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
