import argparse
import json
import os
import sqlite3
import sys
from typing import Any, Dict, Optional

import yaml

from llm_and_me_tools.openapi_tools.openapi_to_tree import (
    get_openapi_path_tree_as_string,
)


def get_schema_as_json_string(
    schema_obj: Optional[Dict[str, Any]], sort_keys: bool = False
) -> Optional[str]:
    """Converts a schema object to a JSON string."""
    if schema_obj is None:
        return None
    return json.dumps(schema_obj, sort_keys=sort_keys)


def create_tables(conn: sqlite3.Connection):
    """Creates the necessary tables in the SQLite database if they don't exist."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id TEXT,
            openapi_version TEXT,
            title TEXT,
            version TEXT,
            tree TEXT,
            raw_spec TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_data_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            schema_name TEXT, -- Original name from components/schemas, e.g., "MyType"
            ref_path TEXT,    -- Full reference path, e.g., "#/components/schemas/MyType"
            schema_json TEXT NOT NULL, -- The actual JSON schema string
            FOREIGN KEY (contract_id) REFERENCES api_contracts (id),
            UNIQUE (contract_id, schema_json), -- Ensures de-duplication by content
            UNIQUE (contract_id, ref_path)     -- Ensures ref_paths are unique if ref_path is NOT NULL
        )
        """
    )
    # SQLite's UNIQUE constraint on a nullable column only enforces uniqueness for non-NULL values.
    # This is the desired behavior: ref_path is unique if specified, otherwise multiple NULLs are allowed.

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            http_verb TEXT NOT NULL,
            operation_id TEXT,
            summary TEXT,
            description TEXT,
            FOREIGN KEY (contract_id) REFERENCES api_contracts (id),
            UNIQUE (contract_id, path, http_verb)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            in_location TEXT NOT NULL, -- query, header, path, cookie
            description TEXT,
            required BOOLEAN,
            schema_id INTEGER, -- FK to api_data_schemas
            FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id),
            FOREIGN KEY (schema_id) REFERENCES api_data_schemas (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_request_bodies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            description TEXT,
            required BOOLEAN,
            content_type TEXT NOT NULL,
            schema_id INTEGER, -- FK to api_data_schemas
            FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id),
            FOREIGN KEY (schema_id) REFERENCES api_data_schemas (id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_id INTEGER NOT NULL,
            status_code TEXT NOT NULL, -- e.g., "200", "404", "default"
            description TEXT,
            content_type TEXT, -- Can be null if no content
            schema_id INTEGER, -- FK to api_data_schemas
            FOREIGN KEY (endpoint_id) REFERENCES api_endpoints (id),
            FOREIGN KEY (schema_id) REFERENCES api_data_schemas (id)
        )
        """
    )
    conn.commit()


def _store_schema_definition_and_get_id(
    schema_definition_obj: Dict[str, Any],
    contract_id: int,
    cursor: sqlite3.Cursor,
    schema_json_to_id_cache: Dict[str, int],
    component_name: Optional[str] = None,
    component_ref_path: Optional[str] = None,
) -> Optional[int]:
    """
    Stores a schema definition if new, or returns existing ID.
    Updates schema_json_to_id_cache.
    If it's a component schema, its name and ref_path are stored.
    An existing anonymous schema can be "claimed" by a component schema if their definitions match.
    """
    schema_json_str = get_schema_as_json_string(schema_definition_obj, sort_keys=True)
    if not schema_json_str:
        return None

    if schema_json_str in schema_json_to_id_cache:
        schema_id = schema_json_to_id_cache[schema_json_str]
        if component_ref_path:  # Trying to store a component schema
            # Check if the existing schema (with same JSON content) is anonymous
            cursor.execute(
                "SELECT schema_name, ref_path FROM api_data_schemas WHERE id = ?",
                (schema_id,),
            )
            existing_details = cursor.fetchone()
            if (
                existing_details and existing_details[1] is None
            ):  # If existing schema has no ref_path (is anonymous)
                try:
                    cursor.execute(
                        "UPDATE api_data_schemas SET schema_name = ?, ref_path = ? WHERE id = ?",
                        (component_name, component_ref_path, schema_id),
                    )
                    # No need to conn.commit() here, will be done at the end of transaction
                except sqlite3.IntegrityError as e_update:
                    # This could happen if component_ref_path conflicts with UNIQUE constraint on (contract_id, ref_path)
                    # (e.g. another schema already has this ref_path)
                    print(
                        f"Warning: Could not update schema {schema_id} with component details {component_name}/{component_ref_path} due to IntegrityError: {e_update}. This might happen if the ref_path is already claimed by a different schema definition.",
                        file=sys.stderr,
                    )
        return schema_id

    # Schema definition not in cache (based on its JSON content), try to insert.
    try:
        cursor.execute(
            "INSERT INTO api_data_schemas (contract_id, schema_name, ref_path, schema_json) VALUES (?, ?, ?, ?)",
            (contract_id, component_name, component_ref_path, schema_json_str),
        )
        schema_id = cursor.lastrowid
        if schema_id is not None:
            schema_json_to_id_cache[schema_json_str] = schema_id
        return schema_id
    except (
        sqlite3.IntegrityError
    ):  # UNIQUE constraint failed (likely on contract_id, schema_json)
        # Schema with this JSON content already exists in DB, fetch its ID.
        cursor.execute(
            "SELECT id FROM api_data_schemas WHERE contract_id = ? AND schema_json = ?",
            (contract_id, schema_json_str),
        )
        row = cursor.fetchone()
        if row:
            schema_id = row[0]
            schema_json_to_id_cache[schema_json_str] = schema_id
            # Similar logic: if it's a component, try to update name/ref_path if the DB entry is anonymous.
            if component_ref_path:
                cursor.execute(
                    "SELECT schema_name, ref_path FROM api_data_schemas WHERE id = ?",
                    (schema_id,),
                )
                existing_details = cursor.fetchone()
                if (
                    existing_details and existing_details[1] is None
                ):  # If existing schema has no ref_path
                    try:
                        cursor.execute(
                            "UPDATE api_data_schemas SET schema_name = ?, ref_path = ? WHERE id = ?",
                            (component_name, component_ref_path, schema_id),
                        )
                    except sqlite3.IntegrityError as e_update:
                        print(
                            f"Warning: Could not update (after fetching due to IntegrityError) schema {schema_id} with component details {component_name}/{component_ref_path} due to IntegrityError: {e_update}.",
                            file=sys.stderr,
                        )
            return schema_id
        # This path should ideally not be reached if IntegrityError was for (contract_id, schema_json)
        print(
            f"Error: IntegrityError on insert but failed to retrieve existing schema for JSON: {schema_json_str[:100]}...",
            file=sys.stderr,
        )
        return None


def save_openapi_spec_to_sqlite(
    openapi_file_path: str, db_file: str, input_contract_title: Optional[str] = None
) -> str:
    try:
        with open(openapi_file_path, "r", encoding="utf-8") as f:
            openapi_content = f.read()
    except FileNotFoundError:
        return f"Error: OpenAPI file not found at {openapi_file_path}"
    except Exception as e:
        return f"Error reading OpenAPI file {openapi_file_path}: {e}"

    try:
        spec: Dict[str, Any] = yaml.safe_load(openapi_content)
    except yaml.YAMLError as e:
        return f"Error parsing OpenAPI content from {openapi_file_path}: {e}"
    except Exception as e:
        return (
            f"An unexpected error occurred during parsing of {openapi_file_path}: {e}"
        )

    if not isinstance(spec, dict):
        return f"Error: OpenAPI content from {openapi_file_path} does not parse to a dictionary."

    component_id = os.path.basename(openapi_file_path)
    tree_string = get_openapi_path_tree_as_string(
        openapi_content, content_type="yaml"
    )  # Assuming YAML

    conn = sqlite3.connect(db_file)
    try:
        create_tables(conn)
        cursor = conn.cursor()

        schema_json_to_id_cache: Dict[
            str, int
        ] = {}  # Maps schema_json_str -> schema_id
        schema_ref_to_id_cache: Dict[
            str, int
        ] = {}  # Maps ref_path (#/components/schemas/Name) -> schema_id

        # 1. Insert into api_contracts table
        info = spec.get("info", {})
        contract_title = input_contract_title or info.get("title", "Untitled Contract")
        openapi_version = spec.get("openapi", "Unknown")
        contract_api_version = info.get("version", "Unknown")

        cursor.execute(
            "INSERT INTO api_contracts (component_id, openapi_version, title, version, tree, raw_spec) VALUES (?, ?, ?, ?, ?, ?)",
            (
                component_id,
                openapi_version,
                contract_title,
                contract_api_version,
                tree_string,
                openapi_content,
            ),
        )
        contract_id = cursor.lastrowid
        if contract_id is None:
            conn.rollback()
            return "Error: Failed to retrieve contract_id after insert."

        # Pass 1.1: Process components/schemas - store all actual definitions
        component_schemas = spec.get("components", {}).get("schemas", {})
        for name, definition_obj in component_schemas.items():
            if not isinstance(definition_obj, dict):
                print(
                    f"Warning: Component schema '{name}' has an invalid definition type: {type(definition_obj)}. Skipping.",
                    file=sys.stderr,
                )
                continue
            if (
                "$ref" in definition_obj
            ):  # This component schema is just an alias to another
                continue  # Will be handled in Pass 1.2 by resolving the ref

            component_ref_path = f"#/components/schemas/{name}"
            schema_id = _store_schema_definition_and_get_id(
                definition_obj,
                contract_id,
                cursor,
                schema_json_to_id_cache,
                component_name=name,
                component_ref_path=component_ref_path,
            )
            if schema_id is not None:
                if component_ref_path not in schema_ref_to_id_cache:
                    schema_ref_to_id_cache[component_ref_path] = schema_id
                else:
                    # Should not happen if component names are unique as per OpenAPI spec.
                    # If spec has duplicate component names, first one wins.
                    print(
                        f"Warning: Duplicate component ref_path '{component_ref_path}' encountered while populating schema_ref_to_id_cache. First definition wins.",
                        file=sys.stderr,
                    )

        # Pass 1.2: Process components/schemas - resolve $refs within components
        for name, definition_obj in component_schemas.items():
            if not isinstance(definition_obj, dict):  # Already warned
                continue

            component_ref_path = f"#/components/schemas/{name}"
            if (
                component_ref_path in schema_ref_to_id_cache
            ):  # Already processed as a direct definition
                continue

            if "$ref" in definition_obj:
                target_ref_path = definition_obj["$ref"]
                if target_ref_path in schema_ref_to_id_cache:
                    schema_ref_to_id_cache[component_ref_path] = schema_ref_to_id_cache[
                        target_ref_path
                    ]
                else:
                    print(
                        f"Warning: Component schema '{name}' references '{target_ref_path}' which could not be resolved from pre-processed component definitions. This might be a dangling or forward reference.",
                        file=sys.stderr,
                    )
            else:
                # This should have been caught in Pass 1.1 unless something is wrong.
                print(
                    f"Internal Warning: Component schema '{name}' was not a $ref and not processed in Pass 1.1.",
                    file=sys.stderr,
                )

        # Pass 2: Iterate through paths and insert into api_endpoints and related tables
        paths = spec.get("paths", {})
        for path_url, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for http_verb, operation in path_item.items():
                if http_verb.lower() not in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                    "head",
                    "trace",
                ] or not isinstance(operation, dict):
                    continue

                operation_id = operation.get("operationId")
                summary = operation.get("summary")
                description = operation.get("description")

                cursor.execute(
                    "INSERT INTO api_endpoints (contract_id, path, http_verb, operation_id, summary, description) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        contract_id,
                        path_url,
                        http_verb.upper(),
                        operation_id,
                        summary,
                        description,
                    ),
                )
                endpoint_id = cursor.lastrowid
                if endpoint_id is None:
                    print(
                        f"Warning: Failed to retrieve endpoint_id for {path_url} {http_verb.upper()}",
                        file=sys.stderr,
                    )
                    continue

                # Process parameters, requestBody, responses
                for item_type in ["parameters", "requestBody", "responses"]:
                    if item_type == "parameters":
                        items_to_process = operation.get(
                            "parameters", []
                        ) + path_item.get("parameters", [])
                        for param_obj in items_to_process:
                            if not isinstance(param_obj, dict):
                                continue
                            schema_obj_to_resolve = param_obj.get("schema")
                            schema_id_for_fk = None
                            if isinstance(schema_obj_to_resolve, dict):
                                if "$ref" in schema_obj_to_resolve:
                                    ref_path = schema_obj_to_resolve["$ref"]
                                    if ref_path in schema_ref_to_id_cache:
                                        schema_id_for_fk = schema_ref_to_id_cache[
                                            ref_path
                                        ]
                                    else:
                                        print(
                                            f"Warning: Parameter schema $ref '{ref_path}' not found in cache for {path_url} {http_verb.upper()}.",
                                            file=sys.stderr,
                                        )
                                else:  # Inline schema definition
                                    schema_id_for_fk = (
                                        _store_schema_definition_and_get_id(
                                            schema_obj_to_resolve,
                                            contract_id,
                                            cursor,
                                            schema_json_to_id_cache,
                                        )
                                    )

                            if param_obj.get("name") and param_obj.get("in"):
                                cursor.execute(
                                    "INSERT INTO api_parameters (endpoint_id, name, in_location, description, required, schema_id) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        endpoint_id,
                                        param_obj.get("name"),
                                        param_obj.get("in"),
                                        param_obj.get("description"),
                                        param_obj.get("required", False),
                                        schema_id_for_fk,
                                    ),
                                )

                    elif item_type == "requestBody":
                        rb_obj = operation.get("requestBody")
                        if isinstance(rb_obj, dict) and isinstance(
                            rb_obj.get("content"), dict
                        ):
                            rb_desc = rb_obj.get("description")
                            rb_req = rb_obj.get("required", False)
                            for content_type, media_type_obj in rb_obj[
                                "content"
                            ].items():
                                if not isinstance(media_type_obj, dict):
                                    continue
                                schema_obj_to_resolve = media_type_obj.get("schema")
                                schema_id_for_fk = None
                                if isinstance(schema_obj_to_resolve, dict):
                                    if "$ref" in schema_obj_to_resolve:
                                        ref_path = schema_obj_to_resolve["$ref"]
                                        if ref_path in schema_ref_to_id_cache:
                                            schema_id_for_fk = schema_ref_to_id_cache[
                                                ref_path
                                            ]
                                        else:
                                            print(
                                                f"Warning: Request body schema $ref '{ref_path}' not found in cache for {path_url} {http_verb.upper()}.",
                                                file=sys.stderr,
                                            )
                                    else:  # Inline schema definition
                                        schema_id_for_fk = (
                                            _store_schema_definition_and_get_id(
                                                schema_obj_to_resolve,
                                                contract_id,
                                                cursor,
                                                schema_json_to_id_cache,
                                            )
                                        )
                                cursor.execute(
                                    "INSERT INTO api_request_bodies (endpoint_id, description, required, content_type, schema_id) VALUES (?, ?, ?, ?, ?)",
                                    (
                                        endpoint_id,
                                        rb_desc,
                                        rb_req,
                                        content_type,
                                        schema_id_for_fk,
                                    ),
                                )

                    elif item_type == "responses":
                        responses_obj = operation.get("responses")
                        if isinstance(responses_obj, dict):
                            for status_code, resp_item_obj in responses_obj.items():
                                if not isinstance(resp_item_obj, dict):
                                    continue
                                resp_desc = resp_item_obj.get("description")
                                resp_content = resp_item_obj.get("content")
                                if isinstance(resp_content, dict):
                                    for (
                                        content_type,
                                        media_type_obj,
                                    ) in resp_content.items():
                                        if not isinstance(media_type_obj, dict):
                                            continue
                                        schema_obj_to_resolve = media_type_obj.get(
                                            "schema"
                                        )
                                        schema_id_for_fk = None
                                        if isinstance(schema_obj_to_resolve, dict):
                                            if "$ref" in schema_obj_to_resolve:
                                                ref_path = schema_obj_to_resolve["$ref"]
                                                if ref_path in schema_ref_to_id_cache:
                                                    schema_id_for_fk = (
                                                        schema_ref_to_id_cache[ref_path]
                                                    )
                                                else:
                                                    print(
                                                        f"Warning: Response schema $ref '{ref_path}' not found in cache for {path_url} {http_verb.upper()} status {status_code}.",
                                                        file=sys.stderr,
                                                    )
                                            else:  # Inline schema definition
                                                schema_id_for_fk = (
                                                    _store_schema_definition_and_get_id(
                                                        schema_obj_to_resolve,
                                                        contract_id,
                                                        cursor,
                                                        schema_json_to_id_cache,
                                                    )
                                                )
                                        cursor.execute(
                                            "INSERT INTO api_responses (endpoint_id, status_code, description, content_type, schema_id) VALUES (?, ?, ?, ?, ?)",
                                            (
                                                endpoint_id,
                                                status_code,
                                                resp_desc,
                                                content_type,
                                                schema_id_for_fk,
                                            ),
                                        )
                                else:  # Response with no content for this status code
                                    cursor.execute(
                                        "INSERT INTO api_responses (endpoint_id, status_code, description, content_type, schema_id) VALUES (?, ?, ?, ?, ?)",
                                        (
                                            endpoint_id,
                                            status_code,
                                            resp_desc,
                                            None,
                                            None,
                                        ),
                                    )
        conn.commit()
        return f"Successfully saved OpenAPI spec '{contract_title}' from '{openapi_file_path}' to {db_file} with contract ID {contract_id}."

    except sqlite3.Error as e:
        conn.rollback()
        return f"SQLite error: {e}"
    except Exception as e:
        conn.rollback()
        return f"An unexpected error occurred: {e}"
    finally:
        conn.close()


def main_cli():
    parser = argparse.ArgumentParser(
        description="Convert an OpenAPI (YAML/JSON) specification to a SQLite database."
    )
    parser.add_argument("--openapi-file", help="Path to the OpenAPI YAML or JSON file.")
    parser.add_argument(
        "--db-file", help="Path to the SQLite database file to create or update."
    )
    parser.add_argument(
        "--title", help="Optional title for the contract in the database."
    )
    args = parser.parse_args()

    if not args.openapi_file or not args.db_file:
        parser.error(
            "Both --openapi-file and --db-file are required."
        )  # sys.exit(2) implicitly
        # No need for explicit sys.exit(1) here as parser.error exits.

    try:
        result_message = save_openapi_spec_to_sqlite(
            openapi_file_path=args.openapi_file,
            db_file=args.db_file,
            input_contract_title=args.title,
        )
        print(result_message)
        if (
            "Error" in result_message or "Warning:" in result_message
        ):  # Check for "Warning:" too
            # Depending on strictness, warnings might also indicate a non-zero exit code.
            # For now, only "Error" causes non-zero exit.
            if "Error" in result_message:
                sys.exit(1)

    except Exception as e:  # Catch any other unexpected errors from save_openapi_spec_to_sqlite if they weren't returned as string
        print(f"An unexpected error occurred in CLI: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
