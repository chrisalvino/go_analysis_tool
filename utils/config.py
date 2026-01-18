"""Configuration management for the Go analysis tool."""

import json
import os
from typing import Dict, Any


class Config:
    """Configuration manager."""

    DEFAULT_CONFIG = {
        'katago': {
            'executable_path': '',
            'config_path': '',
            'model_path': '',
            'max_visits': 200
        },
        'analysis': {
            'error_threshold': 3.0,
            'top_moves_count': 5,
            'analysis_threads': 3  # Number of parallel analysis threads
        },
        'ui': {
            'board_size': 19,
            'cell_size': 35,
            'margin': 25
        }
    }

    def __init__(self, config_file: str = 'config.json'):
        """Initialize configuration.

        Args:
            config_file: Path to config file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                # Merge with defaults for any missing keys
                self._merge_defaults()
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _merge_defaults(self) -> None:
        """Merge default config with loaded config."""
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config[key]:
                        self.config[key][sub_key] = sub_value

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def get_katago_executable(self) -> str:
        """Get KataGo executable path.

        Returns:
            Path to KataGo executable
        """
        return self.get('katago', 'executable_path', '')

    def get_katago_config(self) -> str:
        """Get KataGo config path.

        Returns:
            Path to KataGo config file
        """
        return self.get('katago', 'config_path', '')

    def get_katago_model(self) -> str:
        """Get KataGo model path.

        Returns:
            Path to KataGo model file
        """
        return self.get('katago', 'model_path', '')

    def get_max_visits(self) -> int:
        """Get maximum analysis visits.

        Returns:
            Maximum visits
        """
        return self.get('katago', 'max_visits', 200)

    def get_error_threshold(self) -> float:
        """Get error detection threshold.

        Returns:
            Error threshold in points
        """
        return self.get('analysis', 'error_threshold', 3.0)

    def get_analysis_threads(self) -> int:
        """Get number of parallel analysis threads.

        Returns:
            Number of threads (1-8)
        """
        threads = self.get('analysis', 'analysis_threads', 3)
        # Clamp between 1 and 8
        return max(1, min(8, threads))

    def is_katago_configured(self) -> bool:
        """Check if KataGo is properly configured.

        Returns:
            True if all KataGo paths are set
        """
        exe = self.get_katago_executable()
        config = self.get_katago_config()
        model = self.get_katago_model()

        return bool(exe and config and model and
                   os.path.exists(exe) and
                   os.path.exists(config) and
                   os.path.exists(model))
