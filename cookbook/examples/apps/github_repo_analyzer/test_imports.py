"""
Test imports to verify all modules are working correctly.
"""

import os
import sys


def test_imports():
    """Test importing all our modules."""
    try:
        print("Testing imports...")

        # Import from agents.py
        from agents import (
            analyze_repository,
            build_analysis_prompt,
            get_github_analyzer,
        )

        print("✅ Successfully imported from agents.py")

        # Import from utils.py
        from utils import (
            CUSTOM_CSS,
            about_widget,
            add_message,
            clean_analysis_text,
            ensure_output_dir,
            extract_metrics,
            load_favorites,
            restart_session,
            save_favorites,
            sidebar_widget,
            toggle_favorite,
        )

        print("✅ Successfully imported from utils.py")

        # Import from app.py
        from app import (
            display_analysis,
            display_favorites,
            display_header,
            display_metrics,
            display_sidebar_controls,
            initialize_session_state,
            main,
            run_analysis,
        )

        print("✅ Successfully imported from app.py")

        print("\nAll imports successful!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    test_imports()
