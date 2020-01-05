"""
TODO:
    * add logging in general
    * add logging to :func:`.fail`
"""
import copy
import logging
import pkgutil
import os
import sys
import traceback

import ruamel.yaml

from booktag import exceptions
from booktag.app import argv
from booktag.cli import showscript
from booktag.cli import stdapp
from booktag.utils import collections


def init_config():
    config = collections.GetDotKeyProxy({})
    try:
        raw_config = pkgutil.get_data('booktag', 'config.yaml')
        config.update(ruamel.yaml.YAML(typ='safe').load(raw_config))
    except (ValueError, ruamel.yaml.error.YAMLError) as err:
        raise ValueError('invalid YAML configuration file.') from err
    except OSError:
        # No configuration file
        pass
    return config


def init_logging(config):
    logger = None
    if config['debug']:
        logger = logging.getLogger('booktag')
        logger.setLevel(logging.DEBUG)
        logfile = config['path'].rstrip(os.sep) + '.log'
        handler = logging.FileHandler(logfile, mode='w')
        formatter = logging.Formatter(
            "%(relativeCreated)5.3f [%(name)s.%(funcName)s:%(lineno)s] "
            "[%(levelname)5.5s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL)
    return logger


def fail(prog, msg, logger):
    if logger:
        logger.exception(msg)
    sys.exit('{0}: {1}'.format(prog, msg))


def main():
    args = argv.parse()
    logger = None
    try:
        config = init_config()
        args.apply_user_settings(config)
        logger = init_logging(config)
        tags = args.get_tags() or None
        if config['show']:
            app = showscript.App()
        else:
            app = stdapp.App()
            app.set_tags(tags)
        app.set_config(config)
        app.run()
    except (FileNotFoundError, PermissionError) as err:
        fail(args.prog,
             "cannot access '{0}': {1}".format(err.filename, err.strerror),
             logger)
    except (exceptions.DirectoryIsEmptyError, exceptions.IsASymlinkError,
            exceptions.NotDirectoryOrFileError) as err:
        fail(args.prog,
             "cannot process '{0}': {1}".format(err.filename, err.strerror),
             logger)
    except exceptions.NotAudioContentError:
        fail(args.prog, 'cannot find supported audio files.', None)
    except exceptions.HaltError as err:
        fail(args.prog, err, None)
    except Exception as err:
        fail(args.prog, 'internal error: {0}'.format(err), logger)
