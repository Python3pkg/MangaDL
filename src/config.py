from os import path, makedirs
from configparser import ConfigParser, ExtendedInterpolation
from appdirs import AppDirs


class Config:
    """
    MangaDL configuration management
    """
    CONFIGS = (
        ('Paths', ('manga_dir', 'chapter_dir', 'page_filename')),
        ('Common', ('sites',))
    )

    def __init__(self):
        """
        Initialize a new Config instance
        """
        self.dirs = AppDirs('MangaDL', 'Makoto')

        # Internal file and ConfigParser placeholders
        self._cfgfile = None
        self._config = ConfigParser(interpolation=ExtendedInterpolation())

        # Set the path information
        self.app_config_dir = self.dirs.user_config_dir
        self.app_config_file = "manga-dl.cfg"
        self.app_config_path = path.join(self.app_config_dir, self.app_config_file)

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
        :rtype : configparser.ConfigParser
        """
        # If our config directory doesn't exist, create it
        if not path.exists(self.app_config_dir):
            makedirs(self.app_config_dir, 0o750)

        self._cfgfile = open(self.app_config_path, 'w')

        # Create the config sections
        for config in self.CONFIGS:
            section, settings = config
            # Create config section
            self._config.add_section(section)

            # Assign config settings
            for setting in settings:
                self._config.set(section, setting, '')

        # Save all passed settings
        self._config.read_dict(config_dict)

        # Write and flush the default configuration
        self._config.write(self._cfgfile)
        self._cfgfile.flush()