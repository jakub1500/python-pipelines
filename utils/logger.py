import logging
from utils.environment import env

logging.basicConfig(format='%(asctime)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Logger:

    @classmethod
    def mask_secret_text(cls, text):
        if "general" in env and "secrets" in env["general"] and len(env["general"]["secrets"]) != 0:
            length = len(text)
            masked_text = "*"*length
            print("Warning! Passed unmasked secret to Logger! Auto-masking it!")
            return masked_text
        return text


    @classmethod
    def debug(cls, text):
        text = cls.mask_secret_text(text)
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.debug(text)

    @classmethod
    def info(cls, text):
        text = cls.mask_secret_text(text)
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.info(text)

    @classmethod
    def warning(cls, text):
        text = cls.mask_secret_text(text)
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.warning(text)

    @classmethod
    def error(cls, text):
        text = cls.mask_secret_text(text)
        if env["general"]["relocated_env"]:
            print(text, flush=True)
        else:
            logger.error(text)