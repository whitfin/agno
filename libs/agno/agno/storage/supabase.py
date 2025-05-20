import time
from typing import Any, Dict, List, Literal, Optional, Union

from agno.storage.base import Storage
from agno.storage.session import Session
from agno.storage.session.agent import AgentSession
from agno.storage.session.team import TeamSession
from agno.storage.session.workflow import WorkflowSession
from agno.utils.log import log_debug, log_info, log_warning, logger

try:
    import os

    from supabase import Client, create_client
except ImportError:
    raise ImportError("`supabase` not installed. Please install it using `pip install supabase`")


class SupabaseStorage(Storage):
    def __init__(
        self,
        table_name: str,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        supabase_client: Optional[Client] = None,
        schema_version: int = 1,
        auto_upgrade_schema: bool = False,
        mode: Optional[Literal["agent", "team", "workflow"]] = "agent",
        schema: Optional[str] = None,
    ):
        """
        This class provides agent storage using a Supabase table.

        The following order is used to determine the Supabase connection:
            1. Use the supabase_client if provided
            2. Use the supabase_url and supabase_key
            3. Use environment variables SUPABASE_URL and SUPABASE_KEY
            4. Raise an error if none of the above is provided

        Args:
            table_name (str): Name of the table to store Agent sessions.
            supabase_url (Optional[str]): The Supabase URL to connect to.
            supabase_key (Optional[str]): The Supabase API key.
            supabase_client (Optional[Client]): The Supabase client to use.
            schema_version (int): Version of the schema. Defaults to 1.
            auto_upgrade_schema (bool): Whether to automatically upgrade the schema.
            mode (Optional[Literal["agent", "team", "workflow"]]): The mode of the storage.
            schema (Optional[str]): Database schema to use. Defaults to None (public schema).
        Raises:
            ValueError: If neither supabase_client nor (supabase_url and supabase_key) nor environment variables are provided.
        """
        super().__init__(mode)

        # Initialize the Supabase client
        _client: Optional[Client] = supabase_client

        if _client is None:
            # Try to use provided URL and key
            _url = supabase_url or os.environ.get("SUPABASE_URL")
            _key = supabase_key or os.environ.get("SUPABASE_KEY")

            if not _url or not _key:
                raise ValueError(
                    "Must provide either supabase_client or supabase_url and supabase_key or set SUPABASE_URL and SUPABASE_KEY environment variables"
                )

            _client = create_client(_url, _key)

        # Database attributes
        self.table_name: str = table_name
        self.supabase_url: Optional[str] = supabase_url
        self.supabase_key: Optional[str] = supabase_key
        self.supabase_client: Client = _client
        self.schema: Optional[str] = schema

        # Table schema version
        self.schema_version: int = schema_version
        # Automatically upgrade schema if True
        self.auto_upgrade_schema: bool = auto_upgrade_schema
        self._schema_up_to_date: bool = False

        log_debug(f"Created SupabaseStorage: '{self.table_name}'")

    @property
    def mode(self) -> Literal["agent", "team", "workflow"]:
        """Get the mode of the storage."""
        return super().mode

    @mode.setter
    def mode(self, value: Optional[Literal["agent", "team", "workflow"]]) -> None:
        """Set the mode of the storage."""
        super(SupabaseStorage, type(self)).mode.fset(self, value)  # type: ignore

    def _get_query_builder(self):
        """
        Get the query builder with the appropriate schema.

        Returns:
            The Supabase query builder for the table, with schema if specified.
        """
        if self.schema:
            return self.supabase_client.schema(self.schema).table(self.table_name)
        return self.supabase_client.table(self.table_name)

    def table_exists(self) -> bool:
        """
        Check if the table exists in the database.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        try:
            # Try to fetch a single row from the table
            result = self._get_query_builder().select("session_id").limit(1).execute()
            return True
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                log_debug(f"Table '{self.table_name}' does not exist")
                return False
            elif "404" in str(e) or "not found" in str(e).lower():
                log_debug(f"Table '{self.table_name}' does not exist")
                return False
            else:
                logger.error(f"Error checking if table exists: {e}")
                return False

    def create(self) -> None:
        """
        Create the table if it does not exist.

        Note: This method uses raw SQL through the supabase.rpc() method
        since the Python client doesn't provide direct schema creation methods.
        """
        if not self.table_exists():
            try:
                # Define the SQL to create the table based on the mode
                common_columns = """
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    memory JSONB,
                    session_data JSONB,
                    extra_data JSONB,
                    created_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
                    updated_at BIGINT
                """

                specific_columns = ""
                if self.mode == "agent":
                    specific_columns = """
                        agent_id TEXT,
                        team_session_id TEXT,
                        agent_data JSONB,
                    """
                elif self.mode == "team":
                    specific_columns = """
                        team_id TEXT,
                        team_session_id TEXT,
                        team_data JSONB,
                    """
                elif self.mode == "workflow":
                    specific_columns = """
                        workflow_id TEXT,
                        workflow_data JSONB,
                    """

                schema_prefix = f"{self.schema}." if self.schema else ""
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {schema_prefix}{self.table_name} (
                    {specific_columns}
                    {common_columns}
                );
                """

                # Create indexes based on mode
                index_sql = ""
                if self.mode == "agent":
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_agent_id ON {schema_prefix}{self.table_name}(agent_id);
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id ON {schema_prefix}{self.table_name}(user_id);
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_team_session_id ON {schema_prefix}{self.table_name}(team_session_id);
                    """
                elif self.mode == "team":
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_team_id ON {schema_prefix}{self.table_name}(team_id);
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id ON {schema_prefix}{self.table_name}(user_id);
                    """
                elif self.mode == "workflow":
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_workflow_id ON {schema_prefix}{self.table_name}(workflow_id);
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id ON {schema_prefix}{self.table_name}(user_id);
                    """

                # Execute the SQL through RPC
                self.supabase_client.rpc("exec_sql", {"sql": create_table_sql + index_sql}).execute()

                log_debug(f"Created table: {schema_prefix}{self.table_name}")

            except Exception as e:
                logger.error(f"Could not create table: '{self.table_name}': {e}")
                raise

    def read(self, session_id: str, user_id: Optional[str] = None) -> Optional[Session]:
        """
        Read an Session from the database.

        Args:
            session_id (str): ID of the session to read.
            user_id (Optional[str]): User ID to filter by. Defaults to None.

        Returns:
            Optional[Session]: Session object if found, None otherwise.
        """
        try:
            query = self._get_query_builder().select("*").eq("session_id", session_id)
            if user_id:
                query = query.eq("user_id", user_id)

            result = query.execute()

            if not result.data:
                return None

            data = result.data[0]

            if self.mode == "agent":
                return AgentSession.from_dict(data)
            elif self.mode == "team":
                return TeamSession.from_dict(data)
            elif self.mode == "workflow":
                return WorkflowSession.from_dict(data)

        except Exception as e:
            if "does not exist" in str(e):
                log_debug(f"Table does not exist: {self.table_name}")
                log_debug("Creating table for future transactions")
                self.create()
            else:
                log_debug(f"Exception reading from table: {e}")
        return None

    def get_all_session_ids(
        self,
        user_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = "created_at",
        order_direction: Literal["asc", "desc"] = "desc",
    ) -> List[str]:
        """
        Get all session IDs, optionally filtered by user_id and/or entity_id.

        Args:
            user_id (Optional[str]): The ID of the user to filter by.
            entity_id (Optional[str]): The ID of the agent / workflow to filter by.
            limit (Optional[int]): Maximum number of sessions to return.
            offset (Optional[int]): Number of sessions to skip.
            order_by (Optional[str]): Column to order results by. Defaults to "created_at".
            order_direction (Literal["asc", "desc"]): Order direction. Defaults to "desc".

        Returns:
            List[str]: List of session IDs matching the criteria.
        """
        try:
            query = self._get_query_builder().select("session_id")

            # Apply filters
            query = self._apply_filters(query, user_id, entity_id)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=(order_direction == "desc"))

            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            result = query.execute()

            return [row["session_id"] for row in result.data] if result.data else []

        except Exception as e:
            log_debug(f"Exception reading from table: {e}")
            if "does not exist" in str(e):
                log_debug(f"Table does not exist: {self.table_name}")
                log_debug("Creating table for future transactions")
                self.create()

        return []

    def _apply_filters(self, query, user_id=None, entity_id=None, filters=None):
        """
        Apply filters to the query based on user_id, entity_id, and additional filters.

        Args:
            query: The Supabase query object
            user_id (Optional[str]): User ID to filter by
            entity_id (Optional[str]): Entity ID to filter by (agent_id, team_id, or workflow_id)
            filters (Optional[Dict]): Additional filters to apply

        Returns:
            The query with filters applied
        """
        # Apply standard filters
        if user_id is not None:
            query = query.eq("user_id", user_id)

        if entity_id is not None:
            if self.mode == "agent":
                query = query.eq("agent_id", entity_id)
            elif self.mode == "team":
                query = query.eq("team_id", entity_id)
            elif self.mode == "workflow":
                query = query.eq("workflow_id", entity_id)

        # Apply additional filters if provided
        if filters:
            for column, operation_value in filters.items():
                if isinstance(operation_value, dict):
                    operation, value = next(iter(operation_value.items()))

                    # Apply different operations based on the operation type
                    if operation == "eq":
                        query = query.eq(column, value)
                    elif operation == "neq":
                        query = query.neq(column, value)
                    elif operation == "gt":
                        query = query.gt(column, value)
                    elif operation == "gte":
                        query = query.gte(column, value)
                    elif operation == "lt":
                        query = query.lt(column, value)
                    elif operation == "lte":
                        query = query.lte(column, value)
                    elif operation == "like":
                        query = query.like(column, value)
                    elif operation == "ilike":
                        query = query.ilike(column, value)
                    elif operation == "is":
                        query = query.is_(column, value)
                    elif operation == "in":
                        query = query.in_(column, value)
                    elif operation == "contains":
                        query = query.contains(column, value)
                    elif operation == "not":
                        query = query.not_(column, value)
                else:
                    # Default to equals operation if just a value is given
                    query = query.eq(column, operation_value)

        return query

    def get_all_sessions(
        self,
        user_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = "created_at",
        order_direction: Literal["asc", "desc"] = "desc",
        filters: Optional[Dict[str, Any]] = None,
        count_option: Optional[Literal["exact", "planned", "estimated"]] = None,
    ) -> Union[List[Session], Dict[str, Union[List[Session], int]]]:
        """
        Get all sessions, optionally filtered by user_id and/or entity_id.

        Args:
            user_id (Optional[str]): The ID of the user to filter by.
            entity_id (Optional[str]): The ID of the agent / workflow to filter by.
            limit (Optional[int]): Maximum number of sessions to return.
            offset (Optional[int]): Number of sessions to skip.
            order_by (Optional[str]): Column to order results by. Defaults to "created_at".
            order_direction (Literal["asc", "desc"]): Order direction. Defaults to "desc".
            filters (Optional[Dict[str, Any]]): Additional filters to apply to the query.
            count_option (Optional[Literal["exact", "planned", "estimated"]]): Count option to include with results.

        Returns:
            Union[List[Session], Dict[str, Union[List[Session], int]]]:
                List of Session objects matching the criteria or dict with sessions and count if count_option specified.
        """
        try:
            query = self._get_query_builder().select("*", count=count_option)

            # Apply filters
            query = self._apply_filters(query, user_id, entity_id, filters)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=(order_direction == "desc"))

            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            result = query.execute()

            if not result.data:
                return [] if count_option is None else {"data": [], "count": 0}

            # Convert data to Session objects
            sessions = []
            if self.mode == "agent":
                sessions = [AgentSession.from_dict(row) for row in result.data]
            elif self.mode == "team":
                sessions = [TeamSession.from_dict(row) for row in result.data]
            else:
                sessions = [WorkflowSession.from_dict(row) for row in result.data]

            # Return with count if requested
            if count_option is not None and hasattr(result, "count"):
                return {"data": sessions, "count": result.count}

            return sessions

        except Exception as e:
            log_debug(f"Exception reading from table: {e}")
            if "does not exist" in str(e):
                log_debug(f"Table does not exist: {self.table_name}")
                log_debug("Creating table for future transactions")
                self.create()

        return [] if count_option is None else {"data": [], "count": 0}

    def upgrade_schema(self) -> None:
        """
        Upgrade the schema to the latest version.
        Currently handles adding the team_session_id column for agent mode.
        """
        if not self.auto_upgrade_schema:
            log_debug("Auto schema upgrade disabled. Skipping upgrade.")
            return

        try:
            if self.mode == "agent" and self.table_exists():
                # Check if team_session_id column exists using a raw SQL query
                schema_prefix = f"{self.schema}." if self.schema else ""
                check_column_sql = f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{self.table_name}' 
                AND column_name = 'team_session_id'
                """

                if self.schema:
                    check_column_sql += f" AND table_schema = '{self.schema}'"

                result = self.supabase_client.rpc("exec_sql", {"sql": check_column_sql}).execute()
                column_exists = bool(result.data)

                if not column_exists:
                    log_info(f"Adding 'team_session_id' column to {schema_prefix}{self.table_name}")
                    alter_table_sql = f"ALTER TABLE {schema_prefix}{self.table_name} ADD COLUMN team_session_id TEXT"
                    self.supabase_client.rpc("exec_sql", {"sql": alter_table_sql}).execute()
                    self._schema_up_to_date = True
                    log_info("Schema upgrade completed successfully")
        except Exception as e:
            logger.error(f"Error during schema upgrade: {e}")
            raise

    def upsert(self, session: Session, create_and_retry: bool = True) -> Optional[Session]:
        """
        Insert or update an Session in the database.

        Args:
            session (Session): The session data to upsert.
            create_and_retry (bool): Retry upsert if table does not exist.

        Returns:
            Optional[Session]: The upserted Session, or None if operation failed.
        """
        # Perform schema upgrade if auto_upgrade_schema is enabled
        if self.auto_upgrade_schema and not self._schema_up_to_date:
            self.upgrade_schema()

        try:
            data = {}
            # Common data for all modes
            data.update(
                {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "memory": session.memory,
                    "session_data": session.session_data,
                    "extra_data": session.extra_data,
                    "updated_at": int(time.time()),
                }
            )

            # Mode-specific data
            if self.mode == "agent":
                data.update(
                    {
                        "agent_id": session.agent_id,  # type: ignore
                        "team_session_id": session.team_session_id,  # type: ignore
                        "agent_data": session.agent_data,  # type: ignore
                    }
                )
            elif self.mode == "team":
                data.update(
                    {
                        "team_id": session.team_id,  # type: ignore
                        "team_session_id": session.team_session_id,  # type: ignore
                        "team_data": session.team_data,  # type: ignore
                    }
                )
            elif self.mode == "workflow":
                data.update(
                    {
                        "workflow_id": session.workflow_id,  # type: ignore
                        "workflow_data": session.workflow_data,  # type: ignore
                    }
                )

            # Upsert the data
            self._get_query_builder().upsert(data).execute()

        except Exception as e:
            if create_and_retry and not self.table_exists():
                log_debug(f"Table does not exist: {self.table_name}")
                log_debug("Creating table and retrying upsert")
                self.create()
                return self.upsert(session, create_and_retry=False)
            else:
                log_warning(f"Exception upserting into table: {e}")
                log_warning(
                    "A table upgrade might be required, please review these docs for more information: https://agno.link/upgrade-schema"
                )
                return None

        return self.read(session_id=session.session_id)

    def update(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update specific fields of a session.

        Args:
            session_id (str): The ID of the session to update.
            data (Dict[str, Any]): The data to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            result = self._get_query_builder().update(data).eq("session_id", session_id).execute()
            return bool(result.data)
        except Exception as e:
            log_warning(f"Error updating session: {e}")
            return False

    def delete_session(self, session_id: Optional[str] = None):
        """
        Delete a session from the database.

        Args:
            session_id (Optional[str], optional): ID of the session to delete. Defaults to None.

        Raises:
            Exception: If an error occurs during deletion.
        """
        if session_id is None:
            logger.warning("No session_id provided for deletion.")
            return

        try:
            result = self._get_query_builder().delete().eq("session_id", session_id).execute()
            if not result.data:
                log_debug(f"No session found with session_id: {session_id}")
            else:
                log_debug(f"Successfully deleted session with session_id: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session: {e}")

    def delete_sessions(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple sessions based on filters.

        Args:
            filter_dict (Dict[str, Any]): Filters to determine which sessions to delete.

        Returns:
            int: Number of sessions deleted.
        """
        try:
            query = self._get_query_builder().delete()

            # Apply each filter
            for key, value in filter_dict.items():
                query = query.eq(key, value)

            result = query.execute()
            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Error deleting sessions: {e}")
            return 0

    def drop(self) -> None:
        """
        Drop the table from the database if it exists.
        """
        if self.table_exists():
            schema_prefix = f"{self.schema}." if self.schema else ""
            log_debug(f"Deleting table: {schema_prefix}{self.table_name}")
            try:
                drop_table_sql = f"DROP TABLE IF EXISTS {schema_prefix}{self.table_name}"
                self.supabase_client.rpc("exec_sql", {"sql": drop_table_sql}).execute()
            except Exception as e:
                logger.error(f"Error dropping table: {e}")

    def query_sessions_json(self, columns: str = "*") -> List[Dict[str, Any]]:
        """
        Query sessions and return raw JSON response.
        Useful for more complex queries, such as extracting nested JSON fields.

        Args:
            columns (str): The columns to select, can include JSON paths like "memory->conversation".

        Returns:
            List[Dict[str, Any]]: List of session data as dictionaries.
        """
        try:
            result = self._get_query_builder().select(columns).execute()
            return result.data if result.data else []
        except Exception as e:
            log_warning(f"Error querying sessions: {e}")
            return []

    def execute_rpc(self, function_name: str, params: Dict[str, Any]) -> Any:
        """
        Execute a remote procedure call (RPC) function on the Supabase server.

        Args:
            function_name (str): Name of the Postgres function to call.
            params (Dict[str, Any]): Parameters to pass to the function.

        Returns:
            Any: Result of the RPC call.
        """
        try:
            result = self.supabase_client.rpc(function_name, params).execute()
            return result.data
        except Exception as e:
            log_warning(f"Error executing RPC function '{function_name}': {e}")
            return None

    def __deepcopy__(self, memo):
        """
        Create a deep copy of the SupabaseStorage instance, handling unpickleable attributes.

        Args:
            memo (dict): A dictionary of objects already copied during the current copying pass.

        Returns:
            SupabaseStorage: A deep-copied instance of SupabaseStorage.
        """
        from copy import deepcopy

        # Create a new instance without calling __init__
        cls = self.__class__
        copied_obj = cls.__new__(cls)
        memo[id(self)] = copied_obj

        # Deep copy attributes
        for k, v in self.__dict__.items():
            if k in {"supabase_client"}:
                # Reuse client without copying
                setattr(copied_obj, k, v)
            else:
                setattr(copied_obj, k, deepcopy(v, memo))

        return copied_obj
