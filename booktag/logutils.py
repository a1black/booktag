import logging
import platform
import os
from threading import Lock

import tqdm


if platform.system() == 'Windows':
    LOGFILE = os.path.join(os.path.expandvars('%LOCALAPPDATA'), 'booktag.log')
else:
    LOGFILE = os.path.join(os.path.expanduser('~'), '.booktag.log')


# https://stackoverflow.com/questions/38543506/
class TqdmLoggingHandler(logging.Handler):
    """Handler redirects logger output to :meth:`tqdm.tqdm.write`."""

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.set_lock(Lock())
            tqdm.tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_root_logger(debug=False):
    """Returns root logger."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.ERROR)
    # Setup handler for writing to log file
    logfile = logging.FileHandler(LOGFILE, mode='w')
    logfile.setLevel(logger.level)
    formater = logging.Formatter(
        fmt="%(levelname)4.4s:%(asctime)s:%(message)s", datefmt="%H:%M:%S")
    logfile.setFormatter(formater)
    logger.addHandler(logfile)
    return logger


def setup_tqdm_logger(name=None, debug=False):
    """Returns logger that redirects output to :meth:`tqdm.tqdm.write`."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if debug else logging.WARNING)
    # Setup tqdm handler
    formatter = logging.Formatter(fmt='%(levelname)s: %(message)s')
    handler = TqdmLoggingHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
