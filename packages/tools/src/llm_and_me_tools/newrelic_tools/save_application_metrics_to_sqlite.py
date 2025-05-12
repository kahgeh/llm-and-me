import argparse
import sqlite3
from typing import Optional

from llm_and_me_tools.newrelic_tools.get_apm_entity_by_tag import (
    ApmEntity, get_prod_apm_entities_by_component_tag)
from llm_and_me_tools.newrelic_tools.get_application_metrics import (
    ApplicationMetrics, get_application_metrics)


def create_metrics_table(conn: sqlite3.Connection):
    """Creates the metrics table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            component_id TEXT NOT NULL,
            throughput_rpm REAL,
            error_rate_percentage REAL,
            time_window_from TEXT NOT NULL,
            time_window_to TEXT NOT NULL,
            PRIMARY KEY (component_id, time_window_from, time_window_to)
        )
        """
    )
    conn.commit()


def save_application_metrics_to_sqlite(
    component_tag: str,
    db_file: str,
    start_datetime_iso: Optional[str] = None,
    end_datetime_iso: Optional[str] = None,
) -> str:
    """
    Fetches application metrics for a given component tag and saves them to an SQLite database.

    Args:
        component_tag: The Cortex component tag to identify the New Relic entity.
        db_file: Path to the SQLite database file.
        start_datetime_iso: Optional ISO 8601 start datetime for the metrics window.
        end_datetime_iso: Optional ISO 8601 end datetime for the metrics window.

    Returns:
        A string message indicating the outcome.
    """
    apm_entity: Optional[ApmEntity] = get_prod_apm_entities_by_component_tag(
        component_tag
    )
    if not apm_entity:
        return f"Error: Could not find APM entity for component tag '{component_tag}'."
    if not apm_entity.guid:
        return (
            f"Error: APM entity found for '{component_tag}' but it has no entity.guid."
        )

    app_id = apm_entity.guid

    metrics: Optional[ApplicationMetrics] = get_application_metrics(
        app_id=app_id,
        start_datetime_iso=start_datetime_iso,
        end_datetime_iso=end_datetime_iso,
    )

    if not metrics:
        return f"Error: Could not retrieve application metrics for entity GUID '{app_id}' (component: '{component_tag}')."

    try:
        conn = sqlite3.connect(db_file)
        create_metrics_table(conn)
        cursor = conn.cursor()

        time_window_from_iso = metrics.time_window['from']
        time_window_to_iso = metrics.time_window['to']

        cursor.execute(
            """
            INSERT OR REPLACE INTO metrics (
                component_id, throughput_rpm, error_rate_percentage,
                time_window_from, time_window_to
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                component_tag,
                metrics.throughput_rpm,
                metrics.error_rate_percentage,
                time_window_from_iso,
                time_window_to_iso,
            ),
        )
        conn.commit()
        return (
            f"Successfully saved metrics for component '{component_tag}' "
            f"(entity GUID: {apm_entity.guid}) to '{db_file}'. "
            f"Time window: {time_window_from_iso} to {time_window_to_iso}."
        )
    except sqlite3.Error as e:
        return f"Error saving metrics to SQLite for component '{component_tag}': {e}"
    finally:
        if conn:
            conn.close()


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch New Relic application metrics and save to SQLite."
    )
    parser.add_argument(
        "--component-tag",
        required=True,
        help="Cortex component tag to identify the New Relic entity.",
    )
    parser.add_argument(
        "--db-file", required=True, help="Path to the SQLite database file."
    )
    parser.add_argument(
        "--start-time",
        help="Optional ISO 8601 start datetime for the metrics window (e.g., YYYY-MM-DDTHH:MM:SSZ).",
        default=None,
    )
    parser.add_argument(
        "--end-time",
        help="Optional ISO 8601 end datetime for the metrics window (e.g., YYYY-MM-DDTHH:MM:SSZ).",
        default=None,
    )
    return parser.parse_args()


def main_cli():
    """Command-line interface for the tool."""
    args = parse_args()
    result = save_application_metrics_to_sqlite(
        component_tag=args.component_tag,
        db_file=args.db_file,
        start_datetime_iso=args.start_time,
        end_datetime_iso=args.end_time,
    )
    print(result)


if __name__ == "__main__":
    main_cli()
