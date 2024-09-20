import configparser
from logger import logger
from dataclasses import dataclass
import base64

@dataclass
class Config:
    netid: str
    duo_key: str
    imap_server: str
    email_account: str
    email_password: str
    imap_port: int = 993

    def __init__(self, filename: str = "config.ini"):
        logger.debug(f"Reading config file {filename}")
        config = configparser.ConfigParser()
        if len(config.read(filename)) != 1:
            logger.critical("Failed to read config file.")
            exit(1)
        try:
            self.netid = config["auth"]["netid"]
            self.duo_key = base64.b32encode(config["auth"]["duo_key"].encode())
            self.imap_server = config["email"]["server"]
            try:
                self.imap_port = int(config["email"].get("port", 993))
            except ValueError:
                logger.critical("Invalid IMAP port")
                exit(1)
            self.email_account = config["email"]["address"]
            self.email_password = config["email"]["password"]
        except KeyError as e:
            logger.critical(f"{e} not defined in config file")
            exit(1)


