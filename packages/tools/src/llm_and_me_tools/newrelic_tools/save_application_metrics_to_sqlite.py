import argparse
import json
import sqlite3
from typing import List, Optional

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
    component_tags: List[str],
    account: str,
    db_file: str,
    start_datetime_iso: Optional[str] = None,
    end_datetime_iso: Optional[str] = None,
) -> str:
    """
    Fetches application metrics for given component tags and saves them to an SQLite database.

    Args:
        component_tags: A list of Cortex component tags to identify New Relic entities.
        account: The New Relic account abbreviation.
        db_file: Path to the SQLite database file.
        start_datetime_iso: Optional ISO 8601 start datetime for the metrics window.
        end_datetime_iso: Optional ISO 8601 end datetime for the metrics window.

    Returns:
        A JSON string summarizing the outcome for each component tag.
    """
    results = []
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        create_metrics_table(conn)
        cursor = conn.cursor()

        for component_tag in component_tags:
            result_detail = {"component_tag": component_tag, "result": ""}
            try:
                apm_entity: Optional[ApmEntity] = (
                    get_prod_apm_entities_by_component_tag(
                        component_tag=component_tag, account=account
                    )
                )
                if not apm_entity:
                    result_detail[
                        "result"
                    ] = f"Error: Could not find APM entity for component tag '{component_tag}'."
                    results.append(result_detail)
                    continue
                if not apm_entity.guid:
                    result_detail[
                        "result"
                    ] = f"Error: APM entity found for '{component_tag}' but it has no entity.guid."
                    results.append(result_detail)
                    continue

                app_id = apm_entity.guid

                metrics: Optional[ApplicationMetrics] = get_application_metrics(
                    app_id=app_id,
                    account=account,
                    start_datetime_iso=start_datetime_iso,
                    end_datetime_iso=end_datetime_iso,
                )

                if not metrics:
                    result_detail[
                        "result"
                    ] = f"Error: Could not retrieve application metrics for entity GUID '{app_id}' (component: '{component_tag}')."
                    results.append(result_detail)
                    continue

                time_window_from_iso = metrics.time_window["from"]
                time_window_to_iso = metrics.time_window["to"]

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
                result_detail[
                    "result"
                ] = (
                    f"Success: Saved metrics (entity GUID: {apm_entity.guid}). "
                    f"Time window: {time_window_from_iso} to {time_window_to_iso}."
                )
                results.append(result_detail)

            except Exception as e:
                # Catch any unexpected error during processing for a single tag
                result_detail[
                    "result"
                ] = f"Error processing component tag '{component_tag}': {e}"
                results.append(result_detail)
                # Optionally rollback if needed, though INSERT OR REPLACE is somewhat atomic per row
                # conn.rollback()

    except sqlite3.Error as e:
        # Handle errors related to the database connection itself
        results.append(
            {
                "component_tag": "Database Operation",
                "result": f"Error interacting with SQLite database '{db_file}': {e}",
            }
        )
    finally:
        if conn:
            conn.close()

    return json.dumps(results, indent=2)


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch New Relic application metrics and save to SQLite."
    )
    parser.add_argument(
        "--component-tags",
        required=True,
        help="One or more Cortex component tags(comma separated) to identify New Relic entities.",
        type=lambda t: [s.strip() for s in t.split(',')]
    )
    parser.add_argument(
        "--account",
        required=True,
        help="New Relic account abbreviation (e.g., 'ACC1').",
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
    print(args)
    # args.component_tags is now a list
    if not args.account: # Should be caught by argparse if required=True
        print("Error: --account is required.")
        exit(1)

    result_json = save_application_metrics_to_sqlite(
        component_tags=args.component_tags,
        account=args.account,
        db_file=args.db_file,
        start_datetime_iso=args.start_time,
        end_datetime_iso=args.end_time,
    )
    print(result_json)


if __name__ == "__main__":
    main_cli()
