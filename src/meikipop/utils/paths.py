import logging
import os
import shutil
import sys
from platformdirs import PlatformDirs


def copy_if_missing(old_dir: str, new_dir: str) -> None:
    """Starts a new ankipop folder from an existing meikipop one, so settings and the dictionary carry over.
    Copies rather than moves, so meikipop itself keeps working."""
    if old_dir == new_dir or not os.path.isdir(old_dir) or os.path.exists(new_dir):
        return
    try:
        shutil.copytree(old_dir, new_dir)
    except OSError as e:
        shutil.rmtree(new_dir, ignore_errors=True)  # a half-copied dictionary is worse than downloading a fresh one
        logging.getLogger(__name__).warning(f"Could not copy settings from {old_dir}: {e}")


class MeikiPaths:
    """Centralized path resolution for meikipop."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # Create the platformdirs instance as a composited object
            cls._instance = object.__new__(cls)
            old, new = PlatformDirs("meikipop", appauthor=False), PlatformDirs("ankipop", appauthor=False)
            copy_if_missing(old.user_config_dir, new.user_config_dir)
            copy_if_missing(old.user_data_dir, new.user_data_dir)  # same folder as config on windows/macos: skipped
            cls._instance._platform_dirs = PlatformDirs("ankipop", appauthor=False, ensure_exists=True)
        return cls._instance

    @property
    def is_frozen(self):
        """Check if running as PyInstaller bundle"""
        return getattr(sys, 'frozen', False)

    @property
    def data_dir(self):
        """Location of dictionary.pkl"""
        return self._platform_dirs.user_data_dir
    
    @property
    def config_path(self):
        """Full path to config.ini"""
        return os.path.join(self._platform_dirs.user_config_dir, 'config.ini')
    
    @property
    def dictionary_path(self):
        """Location of dictionary.pkl"""
        return os.path.join(self.data_dir, 'dictionary.pkl')
    
    @property
    def cache_dir(self):
        """Location for cached downloads"""
        return self._platform_dirs.user_cache_dir
    
    @property
    def main_dir(self):
        """Location of bundled resources (icons, etc.)"""
        if self.is_frozen:
            return os.path.join(sys._MEIPASS, 'meikipop')
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def get_resource_path(self, relative_path):
        """Get full path to a bundled resource"""
        return os.path.join(self.main_dir, 'resources', relative_path)


paths = MeikiPaths()