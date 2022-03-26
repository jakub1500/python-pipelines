import logging
from utils.environment import env

logging.basicConfig(format='%(asctime)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Logger:

    @classmethod
    def debug(cls, text):
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.debug(text)

    @classmethod
    def info(cls, text):
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.info(text)

    @classmethod
    def warning(cls, text):
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.warning(text)

    @classmethod
    def error(cls, text):
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.error(text)