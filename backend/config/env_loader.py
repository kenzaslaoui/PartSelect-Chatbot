"""
Centralized environment variable loader.

This module loads .env files from both the root and backend directories,
ensuring all environment variables are available throughout the project.

Should be imported at the start of any main entry point.
"""

import os
from pathlib import Path

def load_env():
    """
    Load environment variables from .env files.

    Searches for and loads .env files in the following order:
    1. backend/.env (takes priority for LLM and backend-specific config)
    2. root/.env (for general app config)

    This ensures backend-specific settings override general settings.
    """
    # Find the project root
    backend_dir = Path(__file__).parent.parent
    root_dir = backend_dir.parent

    env_files = [
        root_dir / '.env',      # Load root .env first
        backend_dir / '.env',   # Then load backend .env (overwrites root if conflicts)
    ]

    try:
        from dotenv import load_dotenv
        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file, override=True)
                print(f"✅ Loaded environment variables from {env_file}")
    except ImportError:
        # Fallback: manual .env loading if python-dotenv not installed
        for env_file in env_files:
            if env_file.exists():
                _load_env_file_manual(env_file)
                print(f"✅ Manually loaded environment variables from {env_file}")


def _load_env_file_manual(env_file: Path) -> None:
    """
    Manually load .env file when python-dotenv is not available.

    Args:
        env_file: Path to the .env file
    """
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key and key not in os.environ:
                        os.environ[key] = value
    except Exception as e:
        print(f"⚠️  Could not load .env file {env_file}: {e}")


# Load environment variables when this module is imported
load_env()
