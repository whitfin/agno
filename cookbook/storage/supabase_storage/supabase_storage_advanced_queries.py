"""
Example of using Supabase's advanced database features with agno

Make sure supabase package is installed:
pip install supabase

Environment variables:
- SUPABASE_URL: Your Supabase URL
- SUPABASE_KEY: Your Supabase API key
"""

import os
import uuid

from agno.storage.session.agent import AgentSession
from agno.storage.supabase import SupabaseStorage

# Initialize Supabase storage with optional schema
supabase_storage = SupabaseStorage(
    table_name="agent_sessions",
    mode="agent",
    schema="ai",  # Optional: specify a schema other than public
)

# Create a table if it doesn't exist
supabase_storage.create()

# Generate some example sessions
agent_ids = ["agent-123", "agent-456", "agent-789"]
session_ids = []

for i, agent_id in enumerate(agent_ids):
    # Create a few sessions for each agent
    for j in range(3):
        session_id = str(uuid.uuid4())
        session_ids.append(session_id)

        agent_session = AgentSession(
            session_id=session_id,
            agent_id=agent_id,
            user_id=f"user-{i % 2 + 1}",  # Two different users
            memory={"conversation": [{"role": "user", "content": f"Test message {j}"}]},
            agent_data={"name": f"Test Agent {i}", "model": "gpt-4", "priority": j + 1},
            session_data={"created": f"2023-08-{i + 1:02d}"},
            extra_data={"tags": [f"tag{j}", f"demo{i}"]},
        )

        supabase_storage.upsert(agent_session)

print(f"Created {len(session_ids)} test sessions")

# Example 1: Get sessions with count
result = supabase_storage.get_all_sessions(count_option="exact")
if isinstance(result, dict):
    print(f"Total sessions: {result['count']}")
    print(f"Retrieved {len(result['data'])} sessions")

# Example 2: Paginated results
page_size = 5
page = 1
paginated = supabase_storage.get_all_sessions(
    limit=page_size,
    offset=(page - 1) * page_size,
    order_by="created_at",
    order_direction="desc",
)

print(f"Page {page}: Retrieved {len(paginated)} sessions")

# Example 3: Complex filtering
filtered = supabase_storage.get_all_sessions(
    filters={
        "agent_id": {"in": agent_ids[:2]},  # First two agent IDs
        "agent_data": {"contains": {"priority": 2}},  # Sessions with priority 2
    }
)

print(f"Found {len(filtered)} sessions with priority 2 for specific agents")

# Example 4: Query nested JSON data
json_result = supabase_storage.query_sessions_json(
    "session_id, agent_id, agent_data->priority as priority"
)
print(f"JSON query returned {len(json_result)} results")
if json_result:
    print(f"First result: {json_result[0]}")

# Example 5: Update specific fields
if session_ids:
    success = supabase_storage.update(
        session_ids[0],
        {"agent_data": {"name": "Updated Agent Name", "model": "gpt-4-turbo"}},
    )
    print(f"Update status: {'Success' if success else 'Failed'}")

# Example 6: Delete sessions with specific criteria
deleted_count = supabase_storage.delete_sessions({"user_id": "user-2"})
print(f"Deleted {deleted_count} sessions for user-2")

# Example 7: RPC function call (if you have a custom function in your Supabase project)
# Uncomment to use if you have the corresponding function in your Supabase project
# result = supabase_storage.execute_rpc(
#     "get_session_stats",
#     {"agent_id_param": "agent-123"}
# )
# print(f"RPC result: {result}")

# Clean up - uncomment to delete all test data
# for session_id in session_ids:
#     if session_id:
#         supabase_storage.delete_session(session_id)

# Or drop the entire table (use with caution)
# supabase_storage.drop()
