import argparse
import json
import sqlite3
from pathlib import Path
import sys

def get_column_names_from_dict(data_dict: dict) -> list[str]:
    """
    Determines column names from the first-level properties of a dictionary.
    """
    if not isinstance(data_dict, dict):
        print("Error: Data for determining columns must be a dictionary (JSON object).", file=sys.stderr)
        sys.exit(1)
    return list(data_dict.keys())

def main():
    parser = argparse.ArgumentParser(description="Create or update a SQLite table from a JSON file.")
    parser.add_argument("--json-file", required=True, type=Path, help="Path to the input JSON file.")
    parser.add_argument("--db-file", required=True, type=Path, help="Path to the SQLite database file.")
    parser.add_argument("--table-name", required=True, type=str, help="Name of the table to create/use.")
    args = parser.parse_args()

    if not args.json_file.exists():
        print(f"Error: JSON file not found at {args.json_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading JSON file: {e}", file=sys.stderr)
        sys.exit(1)

    rows_source_data = []
    column_names = []

    if isinstance(raw_data, list):
        if not raw_data:
            print("JSON array is empty. No data to process.", file=sys.stdout)
            sys.exit(0)
        
        first_item = raw_data[0]
        if not isinstance(first_item, dict):
            print("Error: First item in JSON array is not an object. Cannot determine columns.", file=sys.stderr)
            sys.exit(1)
        column_names = get_column_names_from_dict(first_item)
        rows_source_data = raw_data 
    elif isinstance(raw_data, dict):
        column_names = get_column_names_from_dict(raw_data)
        rows_source_data = [raw_data]
    else:
        print("Error: JSON root must be an object or an array of objects.", file=sys.stderr)
        sys.exit(1)

    if not column_names:
        print("Error: Could not determine column names from JSON data.", file=sys.stderr)
        sys.exit(1)

    # Quote column names to handle spaces or SQL keywords, common in JSON keys
    quoted_column_names_for_sql = [f'"{col}"' for col in column_names]
    
    conn = None
    try:
        args.db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(args.db_file)
        cursor = conn.cursor()

        columns_definition_sql = ", ".join([f"{col_sql} TEXT" for col_sql in quoted_column_names_for_sql])
        create_table_sql = f"CREATE TABLE IF NOT EXISTS \"{args.table_name}\" ({columns_definition_sql})"
        cursor.execute(create_table_sql)

        placeholders_sql = ", ".join(["?"] * len(column_names))
        insert_sql = f"INSERT INTO \"{args.table_name}\" ({', '.join(quoted_column_names_for_sql)}) VALUES ({placeholders_sql})"
        
        processed_rows_for_db = []
        for row_data_item in rows_source_data:
            if not isinstance(row_data_item, dict):
                print(f"Warning: Skipping a row that is not an object: {row_data_item}", file=sys.stderr)
                continue

            current_row_values = []
            for col_name_key in column_names: # Use original names for dict key lookup
                value = row_data_item.get(col_name_key)
                if isinstance(value, (dict, list)):
                    current_row_values.append(json.dumps(value))
                else:
                    # Handles str, int, float, bool, None
                    # SQLite will store them appropriately even with TEXT affinity
                    current_row_values.append(value) 
            processed_rows_for_db.append(tuple(current_row_values))
        
        if processed_rows_for_db:
            cursor.executemany(insert_sql, processed_rows_for_db)
            conn.commit()
            print(f"{len(processed_rows_for_db)} row(s) inserted/updated in table '{args.table_name}' in database '{args.db_file}'.")
        else:
            print("No valid rows found in JSON to insert.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
