import os
import json
import time

from datetime import datetime, UTC as utc_tz
from typing import Dict, Optional, Any


class RTOConfig:
    """Manages RTO configuration and credentials"""

    DEFAULT_CONFIG_DIR = os.path.expanduser("~/.rto")
    CONFIG_FILE = "config.json"
    TOKENS_DIR = "tokens"
    KEYS_DIR = "keys"
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager

        Keyword arguments:
        config_dir -- Directory to store configuration files (default: ~/.rto)
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR

        self.config_path = os.path.join(self.config_dir, self.CONFIG_FILE)

        self.tokens_dir = os.path.join(self.config_dir, self.TOKENS_DIR)

        self.keys_dir = os.path.join(self.config_dir, self.KEYS_DIR)

        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, or create default if it doesn't exist"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)

            except Exception as e:
                print(f"Warning: Could not load config file: {e}")

        return {
            "default_profile": None,
            "working_directory": "/",
            "profiles": {}
        }

    def save_config(self):
        """Save configuration to file"""
        config_dir = os.path.dirname(self.config_path)

        os.makedirs(config_dir, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    def get_default_profile(self) -> Optional[str]:
        """Get the default profile name"""
        return self._config.get("default_profile")

    def set_default_profile(self, profile_name: str):
        """
        Set the default profile

        Keyword arguments:
        profile_name -- Name of the profile to set as default
        """
        if profile_name not in self._config["profiles"]:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        self._config["default_profile"] = profile_name

        self.save_config()

    def get_working_directory(self) -> str:
        """Get the current working directory"""
        return self._config.get("working_directory", "/")

    def set_working_directory(self, directory: str):
        """
        Set the working directory

        Keyword arguments:
        directory -- New working directory
        """
        self._config["working_directory"] = directory

        self.save_config()

    def add_profile(self, profile_name: str, entity_id: str, app_name: str, 
                   deployment_id: str, private_key_path: str, set_default: bool = False):
        """
        Add a new profile

        Keyword arguments:
        profile_name -- Unique name for the profile
        entity_id -- Unique identifier for the entity
        app_name -- Name of the application
        deployment_id -- Unique identifier for the deployment
        private_key_path -- Path to the private key file
        set_default -- Whether to set this profile as the default
        """
        self._config["profiles"][profile_name] = {
            "entity_id": entity_id,
            "app_name": app_name,
            "deployment_id": deployment_id,
            "private_key_path": private_key_path
        }

        if set_default or self._config["default_profile"] is None:
            self._config["default_profile"] = profile_name

        self.save_config()

    def remove_profile(self, profile_name: str):
        """
        Remove a profile

        Keyword arguments:
        profile_name -- Name of the profile to remove
        """
        if profile_name not in self._config["profiles"]:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        del self._config["profiles"][profile_name]

        # Update default profile if needed
        if self._config["default_profile"] == profile_name:
            if self._config["profiles"]:
                self._config["default_profile"] = next(iter(self._config["profiles"].keys()))

            else:
                self._config["default_profile"] = None

        self.save_config()

    def get_profile(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get profile information, using default if profile_name is None

        Keyword arguments:
        profile_name -- Name of the profile to retrieve (default: None)
        """
        if profile_name is None:
            profile_name = self.get_default_profile()

            if profile_name is None:
                raise ValueError("No default profile set and no profile specified")

        if profile_name not in self._config["profiles"]:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        return self._config["profiles"][profile_name]

    def get_token_path(self, profile_name: str) -> str:
        """
        Get the path to the token file for a profile

        Keyword arguments:
        profile_name -- Name of the profile
        """
        os.makedirs(self.tokens_dir, exist_ok=True)

        return os.path.join(self.tokens_dir, f"{profile_name}.token")

    def get_token(self, profile_name: str) -> Optional[tuple]:
        """
        Get a valid token for a profile, if one exists.

        Keyword arguments:
        profile_name -- Name of the profile

        Returns (token, token_expires) tuple if valid, None otherwise
        """
        token_path = self.get_token_path(profile_name)

        if not os.path.exists(token_path):
            return None

        try:
            with open(token_path, 'r') as f:
                token_data = json.load(f)

            # Parse the ISO format expiration date
            if "expires_at" in token_data:
                expires_at = datetime.fromisoformat(token_data["expires_at"])

                # Check if token is still valid
                if expires_at > datetime.now(tz=utc_tz):
                    # Return token and expiration as a tuple
                    return (token_data["token"], expires_at)

            return None

        except Exception:
            return None

    def resolve_path(self, path: str = None) -> str:
        """
        Resolve a path against the current working directory.
        Handles absolute paths, relative paths, ./ and ../ notation.

        If path is None, returns the current working directory.

        Keyword arguments:
        path -- The path to resolve

        Returns:
        str -- The resolved absolute path
        """
        if path is None:
            return self.get_working_directory()

        # If it's already an absolute path, just clean it
        if path.startswith('/'):
            absolute_path = path

        else:
            # Get the current working directory
            current_dir = self.get_working_directory()

            # Handle the case when we're at root
            if current_dir == '/':
                absolute_path = '/' + path
            else:
                absolute_path = current_dir + '/' + path

        # Clean up the path (handle .. and .)
        parts = []

        for part in absolute_path.split('/'):
            if part == '..':
                if parts:  # Don't go above root

                    parts.pop()

            elif part and part != '.':  # Skip empty parts and current dir (.)
                parts.append(part)

        # Construct the clean path
        clean_path = '/' + '/'.join(parts)

        # Remove trailing slash (unless it's root)
        if clean_path != '/' and clean_path.endswith('/'):
            clean_path = clean_path[:-1]

        return clean_path

    def save_token(self, profile_name: str, token: str, expires_at: datetime):
        """Save a token for a profile"""
        token_path = self.get_token_path(profile_name)

        token_data = {
            "token": token,
            "expires_at": expires_at.isoformat()
        }

        os.makedirs(os.path.dirname(token_path), exist_ok=True)

        with open(token_path, 'w') as f:
            json.dump(token_data, f)

    def save_key(self, entity_id: str, private_key: bytes) -> str:
        """
        Save a private key and return the path

        Keyword arguments:
        entity_id -- Unique identifier for the key
        private_key -- The private key in bytes
        """
        os.makedirs(self.keys_dir, exist_ok=True)

        key_path = os.path.join(self.keys_dir, f"{entity_id}_priv_key.pem")

        with open(key_path, 'wb') as f:
            f.write(private_key)

        return key_path