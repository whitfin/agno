"""
Example of using Supabase for workflow storage

Make sure supabase package is installed:
pip install supabase

Environment variables:
- SUPABASE_URL: Your Supabase URL
- SUPABASE_KEY: Your Supabase API key
"""

import os
import uuid

from agno.storage.session.workflow import WorkflowSession
from agno.storage.supabase import SupabaseStorage

# Initialize Supabase storage for workflow sessions
supabase_storage = SupabaseStorage(table_name="workflow_sessions", mode="workflow")

# Create a table if it doesn't exist
supabase_storage.create()

# Example of creating and storing a workflow session
workflow_session = WorkflowSession(
    session_id=str(uuid.uuid4()),
    workflow_id="example-workflow-123",
    user_id="user-456",
    memory={"conversation": []},
    workflow_data={
        "name": "Example Workflow",
        "description": "A simple example workflow",
        "status": "active",
    },
    session_data={"started_at": "2023-07-15T10:30:00Z"},
    extra_data={"tags": ["demo", "supabase"]},
)

# Store the workflow session
stored_session = supabase_storage.upsert(workflow_session)
print(
    f"Stored session ID: {stored_session.session_id if stored_session else 'Failed to store'}"
)

# Retrieve all sessions for this workflow
all_sessions = supabase_storage.get_all_sessions(entity_id="example-workflow-123")
print(f"Found {len(all_sessions)} sessions for this workflow")

# Retrieve all session IDs for this workflow
session_ids = supabase_storage.get_all_session_ids(entity_id="example-workflow-123")
print(f"Session IDs: {session_ids}")

# Clean up - delete the session we created (commented out for safety)
# supabase_storage.delete_session(workflow_session.session_id)

# Optional: Drop the table when done (commented out for safety)
# supabase_storage.drop()
