"""
Example of using Supabase for team storage

Make sure supabase package is installed:
pip install supabase

Environment variables:
- SUPABASE_URL: Your Supabase URL
- SUPABASE_KEY: Your Supabase API key
"""

import os
import uuid

from agno.storage.session.team import TeamSession
from agno.storage.supabase import SupabaseStorage

# Initialize Supabase storage for team sessions
supabase_storage = SupabaseStorage(table_name="team_sessions", mode="team")

# Create a table if it doesn't exist
supabase_storage.create()

# Example of creating and storing a team session
team_session = TeamSession(
    session_id=str(uuid.uuid4()),
    team_id="example-team-123",
    team_session_id=str(uuid.uuid4()),
    user_id="user-456",
    memory={
        "conversation": [
            {"role": "user", "content": "Hello team!"},
            {
                "role": "agent",
                "agent_id": "team-lead",
                "content": "Hello! How can we help you today?",
            },
        ]
    },
    team_data={
        "name": "Support Team",
        "members": [
            {"agent_id": "team-lead", "name": "Team Lead", "role": "lead"},
            {
                "agent_id": "tech-support",
                "name": "Technical Support",
                "role": "support",
            },
            {
                "agent_id": "customer-service",
                "name": "Customer Service",
                "role": "service",
            },
        ],
        "status": "active",
    },
    session_data={"started_at": "2023-07-15T10:30:00Z"},
    extra_data={"priority": "high", "tags": ["support", "onboarding"]},
)

# Store the team session
stored_session = supabase_storage.upsert(team_session)
print(
    f"Stored session ID: {stored_session.session_id if stored_session else 'Failed to store'}"
)

# Retrieve the session
retrieved_session = supabase_storage.read(team_session.session_id)
if retrieved_session:
    print(f"Retrieved team: {retrieved_session.team_data.get('name')}")
    print(f"Team members: {len(retrieved_session.team_data.get('members', []))}")
    print(f"Memory entries: {len(retrieved_session.memory.get('conversation', []))}")

# Retrieve all sessions for a specific user
user_sessions = supabase_storage.get_all_sessions(user_id="user-456")
print(f"Found {len(user_sessions)} sessions for user-456")

# Retrieve all sessions for this team
team_sessions = supabase_storage.get_all_sessions(entity_id="example-team-123")
print(f"Found {len(team_sessions)} sessions for this team")

# Clean up - delete the session we created (commented out for safety)
# supabase_storage.delete_session(team_session.session_id)

# Optional: Drop the table when done (commented out for safety)
# supabase_storage.drop()
