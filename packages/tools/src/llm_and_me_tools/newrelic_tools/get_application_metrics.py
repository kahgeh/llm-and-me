import argparse
import datetime
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# NEW_RELIC_API_BASE_URL = "https://api.newrelic.com/v2" # V2 API Base URL, no longer primary
NERDGRAPH_API_URL = "https://api.newrelic.com/graphql"  # NerdGraph API URL
NEW_RELIC_API_KEY_ENV_VAR = "NEW_RELIC_API_KEY"

load_dotenv()


# --- Pydantic Models for NerdGraph API Response ---


# For initial entity query to get accountId
class EntityDetails(BaseModel):
    accountId: int
    name: Optional[str] = None  # Useful for debugging or context


class ActorWithEntityDetails(BaseModel):
    entity: Optional[EntityDetails] = None


class ResponseDataWithEntityDetails(BaseModel):
    actor: Optional[ActorWithEntityDetails] = None


class GraphqlEntityResponse(BaseModel):  # For fetching accountId
    data: Optional[ResponseDataWithEntityDetails] = None
    errors: Optional[List[Dict[str, Any]]] = None


# For NRQL query response
class NrqlResult(BaseModel):
    throughput_rpm: Optional[float] = Field(None, alias="throughput_rpm")
    error_rate_percentage: Optional[float] = Field(
        None, alias="error_rate_percent"
    )  # Expecting 0-100

    class Config:
        extra = "allow"  # Allow other fields that might come from NRQL


class NrqlQueryData(BaseModel):
    results: List[NrqlResult] = []
    # metadata: Optional[Dict[str, Any]] = None # If we need metadata like timeWindow


class AccountNrqlData(BaseModel):
    nrql: Optional[NrqlQueryData] = None


class ActorWithAccountNrql(BaseModel):
    account: Optional[AccountNrqlData] = None


class ResponseDataWithAccountNrql(BaseModel):
    actor: Optional[ActorWithAccountNrql] = None


class GraphqlNrqlResponse(BaseModel):  # For NRQL results
    data: Optional[ResponseDataWithAccountNrql] = None
    errors: Optional[List[Dict[str, Any]]] = None


# --- Pydantic Model for Tool Output ---
class ApplicationMetrics(BaseModel):
    app_id: str  # This will be the entityGuid
    time_window: Dict[str, str]
    throughput_rpm: Optional[float] = None
    error_rate_percentage: Optional[float] = (
        None  # Will be derived if error_rate and request_count are present
    )


def _get_new_relic_api_key() -> str:
    api_key = os.getenv(NEW_RELIC_API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(
            f"New Relic API key not found. Set the {NEW_RELIC_API_KEY_ENV_VAR} environment variable."
        )
    return api_key


# Helper function to execute a single NRQL query
def _execute_nrql_query(
    account_id: int,
    nrql_query_str: str,
    headers: Dict[str, str],
    timeout: int = 70,  # Default HTTP timeout for the request
) -> Tuple[
    Optional[NrqlResult], Optional[Dict[str, Any]]
]:  # (parsed_result, raw_json_response)
    """
    Executes a single NRQL query via the NerdGraph API.
    Returns the parsed first result and the raw JSON response.
    """
    # The NRQL query itself can have a timeout, set to 60s here.
    # The overall HTTP request timeout is `timeout`.
    metrics_gql_query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          nrql(query: "{nrql_query_str}", timeout: 60) {{
            results
          }}
        }}
      }}
    }}
    """
    raw_response_json: Optional[Dict[str, Any]] = None
    try:
        response_raw = requests.post(
            NERDGRAPH_API_URL,
            headers=headers,
            json={"query": metrics_gql_query},
            timeout=timeout,
        )
        response_raw.raise_for_status()
        raw_response_json = response_raw.json()
        parsed_response = GraphqlNrqlResponse(**raw_response_json)

        if parsed_response.errors:
            print(
                f"Warning: NerdGraph API error during NRQL query ('{nrql_query_str[:100]}...'): {parsed_response.errors}"
            )
            return None, raw_response_json

        if (
            not parsed_response.data
            or not parsed_response.data.actor
            or not parsed_response.data.actor.account
            or not parsed_response.data.actor.account.nrql
        ):
            print(
                f"Warning: NRQL query ('{nrql_query_str[:100]}...') did not return the expected data structure."
            )
            return None, raw_response_json

        results = parsed_response.data.actor.account.nrql.results
        if results and len(results) > 0:
            # Assuming the first result contains all aggregated data we need for that query
            return results[0], raw_response_json
        else:
            print(
                f"Warning: No results found for NRQL query: '{nrql_query_str[:100]}...'"
            )
            return None, raw_response_json

    except requests.exceptions.RequestException as e:
        print(
            f"Warning: RequestException for NRQL query ('{nrql_query_str[:100]}...'): {e}"
        )
        return (
            None,
            raw_response_json,
        )  # Return raw response if available, else it's None
    except ValueError as e:  # JSONDecodeError
        print(
            f"Warning: JSONDecodeError for NRQL query ('{nrql_query_str[:100]}...'): {e}"
        )
        return None, None  # No raw response if JSON decoding failed


def get_application_metrics(
    app_id: str,  # This is the entityGuid
    start_datetime_iso: Optional[str] = None,  # Expect ISO 8601 format string
    end_datetime_iso: Optional[str] = None,  # Expect ISO 8601 format string
) -> ApplicationMetrics:
    """Fetches key performance metrics for a New Relic application.

    Requires the NEW_RELIC_API_KEY environment variable to be set.
    Metrics are fetched for 'Web' transaction types.
    Time format for start_datetime_iso and end_datetime_iso should be ISO 8601
    (e.g., "2023-01-01T00:00:00+00:00" or "2023-01-01T00:00:00Z").
    If start_datetime_iso is not provided, it defaults to 90 days before end_datetime_iso (or now).
    If end_datetime_iso is not provided, it defaults to the current time.

    Args:
        app_id: The New Relic Application Entity GUID.
        start_datetime_iso: Optional start time for the metrics window (ISO 8601).
        end_datetime_iso: Optional end time for the metrics window (ISO 8601).

    Returns:
        An ApplicationMetrics object containing throughput and error rate.
    """
    api_key = _get_new_relic_api_key()
    headers = {"Api-Key": api_key, "Content-Type": "application/json"}

    transaction_type = "Web"
    # Step 1: Fetch accountId using the entityGuid (app_id)
    entity_query = f"""
    {{
      actor {{
        entity(guid: "{app_id}") {{
          accountId
          name
        }}
      }}
    }}
    """
    try:
        entity_response_raw = requests.post(
            NERDGRAPH_API_URL, headers=headers, json={"query": entity_query}, timeout=30
        )
        entity_response_raw.raise_for_status()
        entity_response_json = entity_response_raw.json()
        parsed_entity_response = GraphqlEntityResponse(**entity_response_json)

        if parsed_entity_response.errors:
            raise RuntimeError(
                f"NerdGraph API error when fetching entity details: {parsed_entity_response.errors}"
            )
        if (
            not parsed_entity_response.data
            or not parsed_entity_response.data.actor
            or not parsed_entity_response.data.actor.entity
        ):
            raise RuntimeError(
                f"Could not retrieve entity details (accountId) for GUID {app_id}."
            )

        account_id = parsed_entity_response.data.actor.entity.accountId
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Error fetching entity details from New Relic NerdGraph API: {e}"
        ) from e
    except ValueError as e:
        raise RuntimeError(
            f"Error decoding JSON response for entity details: {e}"
        ) from e

    # Step 2: Determine time window
    if end_datetime_iso:
        end_dt = datetime.datetime.fromisoformat(
            end_datetime_iso.replace("Z", "+00:00")
        )
    else:
        end_dt = datetime.datetime.now(datetime.timezone.utc)

    if start_datetime_iso:
        start_dt = datetime.datetime.fromisoformat(
            start_datetime_iso.replace("Z", "+00:00")
        )
    else:
        start_dt = end_dt - datetime.timedelta(days=90)  # Default to last 90 days

    start_iso_query_format = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_iso_query_format = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    time_window_nrql = (
        f"SINCE '{start_iso_query_format}' UNTIL '{end_iso_query_format}'"
    )

    # Step 3: Initialize output and storage for raw responses
    output_metrics_dict: Dict[str, Any] = {
        "app_id": app_id,
        "time_window": {"from": start_iso_query_format, "to": end_iso_query_format},
    }

    # Step 4: Define and execute NRQL queries
    query_tp_str = f"SELECT rate(count(apm.service.transaction.duration), 1 minute) AS throughput_rpm FROM Metric WHERE (transactionType='{transaction_type}') AND (entity.guid = '{app_id}') LIMIT MAX TIMESERIES {time_window_nrql}"
    parsed_tp, _ = _execute_nrql_query(account_id, query_tp_str, headers)
    if parsed_tp and parsed_tp.throughput_rpm is not None:
        output_metrics_dict["throughput_rpm"] = parsed_tp.throughput_rpm

    query_er_str = f"SELECT 100*sum(apm.service.error.count['count']) / count(apm.service.transaction.duration) AS error_rate_percent FROM Metric WHERE transactionType='{transaction_type}' AND entityGuid = '{app_id}' {time_window_nrql}"
    parsed_er, _ = _execute_nrql_query(account_id, query_er_str, headers)
    if parsed_er and parsed_er.error_rate_percentage is not None:
        output_metrics_dict["error_rate_percentage"] = (
            parsed_er.error_rate_percentage
        )  # This is 0-100

    return ApplicationMetrics(**output_metrics_dict)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch New Relic application metrics using NerdGraph."
    )
    parser.add_argument(
        "--app-id",
        type=str,
        required=False,  # Made optional to prefer env var if not provided
        help="New Relic Application Entity GUID. If not provided, NEW_RELIC_TEST_APP_ID env var is used.",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        help="Start time for metrics query in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ). Defaults to 90 days ago.",
    )
    parser.add_argument(
        "--end-time",
        type=str,
        help="End time for metrics query in ISO 8601 format (e.g., YYYY-MM-DDTHH:MM:SSZ). Defaults to now.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    cli_app_id = args.app_id
    env_app_id = os.getenv("NEW_RELIC_TEST_APP_ID")  # This should be an Entity GUID

    app_id_to_use = cli_app_id or env_app_id

    if not app_id_to_use:
        print(
            "Error: Application Entity GUID not provided. "
            "Set it with --app-id or the NEW_RELIC_TEST_APP_ID environment variable."
        )
        exit(1)
    if not os.getenv(NEW_RELIC_API_KEY_ENV_VAR):
        print(
            f"Error: New Relic API key not found. Set the {NEW_RELIC_API_KEY_ENV_VAR} environment variable."
        )
        exit(1)

    try:
        print(f"--- Fetching WEB metrics for Entity GUID: {app_id_to_use} ---")
        web_metrics = get_application_metrics(
            app_id=app_id_to_use,
            start_datetime_iso=args.start_time,
            end_datetime_iso=args.end_time,
        )
        print(web_metrics.model_dump_json(indent=2, exclude_none=True))

    except Exception as e:
        print(f"Error: {e}")
