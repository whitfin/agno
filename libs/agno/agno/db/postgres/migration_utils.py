"""Simple migration utils for the PostgresDb class"""

from typing import Dict, Set

from sqlalchemy import Engine, text
from sqlalchemy.inspection import inspect

from agno.db.postgres.schemas import get_table_schema_definition
from agno.utils.log import log_debug, log_error, log_info, log_warning


def get_missing_columns(engine: Engine, table_name: str, table_type: str, db_schema: str) -> Set[str]:
    """Return columns missing from the given table"""
    try:
        expected_schema = get_table_schema_definition(table_type)
        expected_columns = {col for col in expected_schema.keys() if not col.startswith("_")}

        inspector = inspect(engine)
        existing_columns = {col["name"] for col in inspector.get_columns(table_name, schema=db_schema)}

        return expected_columns - existing_columns

    except Exception as e:
        log_error(f"Error checking missing columns: {e}")
        return set()


def is_safe_column_addition(column_config: Dict) -> bool:
    """Return True if adding this column is a non-breaking change"""
    return column_config.get("nullable", True) or "default" in column_config


def add_missing_columns(engine: Engine, table_name: str, table_type: str, db_schema: str) -> bool:
    """Update the given table with all missing columns"""
    try:
        missing_columns = get_missing_columns(engine, table_name, table_type, db_schema)
        if not missing_columns:
            log_debug(f"No missing columns found for table '{table_name}'")
            return True

        expected_schema = get_table_schema_definition(table_type)
        unsafe_columns = []

        with engine.begin() as conn:
            for col_name in missing_columns:
                col_config = expected_schema[col_name]

                if not is_safe_column_addition(col_config):
                    unsafe_columns.append(col_name)
                    continue

                col_type = col_config["type"]()
                nullable = "NULL" if col_config.get("nullable", True) else "NOT NULL"

                alter_sql = f"ALTER TABLE {db_schema}.{table_name} ADD COLUMN {col_name} {col_type} {nullable}"

                # Handle default values
                if "default" in col_config:
                    alter_sql += f" DEFAULT {col_config['default']}"

                conn.execute(text(alter_sql))
                log_info(f"Added column {col_name} to {db_schema}.{table_name}")

        if unsafe_columns:
            log_warning(f"Unsafe columns requiring manual migration: {unsafe_columns}")
            return False

        return True

    except Exception as e:
        log_error(f"Error adding missing columns: {e}")
        return False


def needs_migration(engine: Engine, table_name: str, table_type: str, db_schema: str) -> bool:
    """Return true if the given table differs from its expected schema"""
    missing_columns = get_missing_columns(engine, table_name, table_type, db_schema)
    return len(missing_columns) > 0


def migrate_if_needed(engine: Engine, table_name: str, table_type: str, db_schema: str) -> None:
    """Check if the given table needs a migration, and apply the migration if it does

    Returns:
        True if no migration is needed or the migration was applied successfully, False otherwise
    """
    if not needs_migration(engine, table_name, table_type, db_schema):
        return

    if add_missing_columns(engine, table_name, table_type, db_schema):
        return

    raise Exception(f"A migration that can't be auto-applied is needed in table '{table_name}'")
