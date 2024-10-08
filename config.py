import configparser
import sys
import base64
from dataclasses import dataclass
from typing import List
from logger import logger
from integrations.integration import Integration
from integrations import AVAILABLE_INTEGRATIONS

@dataclass
class MailConfig:
    imap_server: str
    email_account: str
    email_password: str
    imap_port: int = 993

    def __init__(self, section: dict):
        self.imap_server = section["server"]
        try:
            self.imap_port = int(section.get("port", 993))
        except ValueError:
            logger.critical("Invalid IMAP port")
            sys.exit(1)
        self.email_account = section["address"]
        self.email_password = section["password"]

@dataclass
class AuthConfig:
    netid: str
    duo_key: str

    def __init__(self, section: dict):
        self.netid = section["netid"]
        self.duo_key = base64.b32encode(section["duo_key"].encode())


@dataclass
class Config:
    mail_config: MailConfig
    auth_config: AuthConfig
    enabled_integrations: List[Integration]

    def __init__(self, filename: str = "config.ini"):
        self.enabled_integrations = []
        logger.debug("Reading config file %s", filename)
        config = configparser.ConfigParser()
        if len(config.read(filename)) != 1:
            logger.critical("Failed to read config file.")
            sys.exit(1)
        try:
            self.mail_config = MailConfig(config["email"])
            self.netid_config = AuthConfig(config["auth"])
        except KeyError as e:
            logger.critical("%s not defined in config file", e)
            sys.exit(1)
        try:
            integration_config = config["integrations"]
            for integration_name, integration in AVAILABLE_INTEGRATIONS.items():
                if integration_config[integration_name]:
                    logger.info("Enabled %s.", integration.__name__)
                    self.enabled_integrations.append(integration())
        except Exception as e:
            logger.warning("Error when parsing integration configuration: %s", e)
