"""
Example of using Supabase for agent storage

Make sure supabase package is installed:
pip install supabase

Environment variables:
- SUPABASE_URL: Your Supabase URL
- SUPABASE_KEY: Your Supabase API key
"""

import os

from agno.storage.supabase import SupabaseStorage

# Initialize Supabase storage for agent sessions
supabase_storage = SupabaseStorage(
    table_name="agent_sessions",
    # Optionally provide the URL and key directly, otherwise they'll be read from environment variables
    # supabase_url=os.environ.get("SUPABASE_URL"),
    # supabase_key=os.environ.get("SUPABASE_KEY"),
    mode="agent",
)

# Make sure the table exists
supabase_storage.create()
