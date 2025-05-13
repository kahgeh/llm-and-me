import argparse
import datetime
import sqlite3
import sys

from .get_last_processing_entry import ProcessingHistoryEntry


def create_processing_history_table(conn: sqlite3.Connection):
    """
    Creates the processing_history table if it doesn't exist.
    The table uses a composite primary key (entity_id, processing_type, key)
    to ensure that only the last entry for this combination is stored,
    effectively replacing older entries on conflict.
    """
    cursor = conn.cursor()
    cursor.execute(
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


def save_processing_entry(db_file: str, entry: ProcessingHistoryEntry):
    """
    Saves a ProcessingHistoryEntry to the SQLite database.
    If an entry with the same entity_id, processing_type, and key already exists,
    it will be replaced.

    Args:
        db_file: Path to the SQLite database file.
        entry: The ProcessingHistoryEntry object to save.
    """
    with sqlite3.connect(
        db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    ) as conn:
        create_processing_history_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO processing_history (entity_id, processing_type, key, value, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.entity_id,
                entry.processing_type,
                entry.key,
                entry.value,
                entry.timestamp.isoformat(),
            ),
        )
        conn.commit()


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Save a processing history entry to an SQLite database."
    )
    parser.add_argument("db_file", help="Path to the SQLite database file.")
    parser.add_argument("entity_id", help="The ID of the entity.")
    parser.add_argument("processing_type", help="The type of processing.")
    parser.add_argument("key", help="The key for the processing status.")
    parser.add_argument("value", help="The value to store.")
    return parser.parse_args()


def main():
    """Main function for the command-line interface."""
    args = parse_args()

    current_timestamp = datetime.datetime.now(datetime.timezone.utc)
    entry = ProcessingHistoryEntry(
        entity_id=args.entity_id,
        processing_type=args.processing_type,
        key=args.key,
        value=args.value,
        timestamp=current_timestamp,
    )

    try:
        save_processing_entry(args.db_file, entry)
        print(f"Successfully saved processing entry to '{args.db_file}'.")
        print(entry.model_dump_json(indent=2))
    except sqlite3.Error as e:
        print(f"Error saving processing entry: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
