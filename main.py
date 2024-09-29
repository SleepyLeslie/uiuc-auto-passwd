#!/usr/bin/env python3

from config import Config
from logger import logger
from netid_center import NetIDCenter
from reset_url_getter import ResetURLGetter
from passgen import generate_passwd

config = Config("config.ini")
netid_center = NetIDCenter(config)
reset_url_getter = ResetURLGetter(config)

request_timestamp = netid_center.request_email()
logger.info("Requested password reset email at %s", request_timestamp)
reset_url = reset_url_getter.get(request_timestamp)
new_passwd = generate_passwd()
logger.info("Resetting password.")
netid_center.perform_reset(reset_url, new_passwd)
for integration in config.enabled_integrations:
    logger.info("Invoking %s.", integration.__class__.__name__)
    integration.execute(new_passwd)
