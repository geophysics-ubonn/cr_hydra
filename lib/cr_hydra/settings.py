"""Manage settings, for now only by means of a config file
"""
import os
import configparser


def _find_best_config_file():
    """Look for a configuration file in certain locations of the file system

    Returns
    -------
    filename : None|str
        None if no config file was found, otherwise an absolute path to the
        configuration file
    """

    # look at these file paths in increasing priority
    locations = [
        '/etc/crhydra/crhydra.cfg',
        os.getenv('HOME') + os.sep + '.crhydra.cfg',
        os.getcwd() + os.sep + 'crhydra.cfg',
    ]

    config_file = None
    for filename in locations:
        if os.path.isfile(filename):
            config_file = os.path.abspath(filename)
    return config_file


def get_config():
    """Return the configuration of crhydra, if a config file is available
    """
    config_file = _find_best_config_file()
    if config_file is None:
        raise IOError(
            'No config file was found! It is required to supply the database' +
            ' credentials!'
        )
    config = configparser.ConfigParser()
    config.read(config_file)
    return config
