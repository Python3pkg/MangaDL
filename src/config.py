from os import path, makedirs
from configparser import ConfigParser, ExtendedInterpolation
from appdirs import AppDirs


class Config:
    """
    MangaDL configuration management
    """
    CONFIGS = (
        ('Paths', ('manga_dir', 'chapter_dir', 'series_dir', 'volume_dir' 'page_filename')),
        ('Common', ('sites', 'synonyms', 'debug'))
    )

    def __init__(self):
        """
        Initialize a new Config instance
        """
        self.dirs = AppDirs('MangaDL', 'Makoto')

        # Internal file and ConfigParser placeholders
        self._app_cfgfile = None
        self._app_config = ConfigParser(interpolation=ExtendedInterpolation())

        # Set the path information
        self.app_config_dir = self.dirs.user_config_dir
        self.app_config_file = "manga-dl.cfg"
        self.app_config_path = path.join(self.app_config_dir, self.app_config_file)

    def app_config(self):
        """
        Return the application configuration
        :rtype : ConfigParser
        """
        self._app_config.read(self.app_config_path)
        return self._app_config

    def app_config_exists(self):
        """
        Check whether a user configuration file for MangaDL exists
        :rtype : bool
        """
        if not path.isdir(self.app_config_dir):
            return False

        if not path.isfile(self.app_config_path):
            return False

        return True

    def app_config_create(self, config_dict):
        """
        Create and return a new configuration file
        :param config_dict: A dictionary of configuration options
        :type  config_dict: dict of dict

        :return: An instantiated and loaded ConfigParser instance
        :rtype : ConfigParser
        """
        # If our config directory doesn't exist, create it
        if not path.exists(self.app_config_dir):
            makedirs(self.app_config_dir, 0o750)

        self._app_cfgfile = open(self.app_config_path, 'w')

        # Create the config sections
        for config in self.CONFIGS:
            section, settings = config
            # Create config section
            self._app_config.add_section(section)

            # Assign config settings
            for setting in settings:
                self._app_config.set(section, setting, '')

        # Save all passed settings
        self._app_config.read_dict(config_dict)

        # Write and flush the default configuration
        self._app_config.write(self._app_cfgfile)
        self._app_cfgfile.flush()