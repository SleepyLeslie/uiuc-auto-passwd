#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import json
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone, timedelta
import string
import random
import pyotp
from consts import *
from config import Config
from logger import logger
import time

config = Config("config.ini")

totp = pyotp.TOTP(config.duo_key, interval=30, digits=6)
mail = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)

def request_email() -> datetime:
    logger.info("Preparing...")
    sess = requests.session()
    # Set up a session and get a JSESSIONID.
    sess.get(f"{IDSERVER_ENDPOINT}/start")
    # Tell the system our NetID.
    sess.post(f"{IDSERVER_ENDPOINT}/postNetId", data={"netId": config.netid})

    logger.info("Starting authentication...")
    # Request to reset the password.
    try_reset_resp = sess.get(f"{IDSERVER_ENDPOINT}/forgottenPWoptions", allow_redirects=False)
    # This attempt should take us to Duo.
    assert try_reset_resp.status_code == 302
    duo_location = try_reset_resp.headers["location"]
    # This URL looks like https://api-cd3ecedb.duosecurity.com/oauth/v1/authorize
    #   ?scope=openid
    #   &response_type=code
    #   &redirect_uri=https://identity.uillinois.edu/iamFrontEnd/iam/authenticationDone
    #   &client_id=<SOMETHING>
    #   &request=<VERY_LONG_STRING>
    # Access the given URL. It returns 303 and redirects us again to a "frame" endpoint.
    auth_init_resp = sess.get(duo_location, allow_redirects=False)
    frame_location = DUO_ENDPOINT + auth_init_resp.headers["location"]
    # This URL looks like https://api-cd3ecedb.duosecurity.com/frame/frameless/v4/auth
    #   ?sid=frameless-<SOME_UUID>
    #   &tx=<VERY_LONG_STRING>
    #   &req-trace-group=<SOMETHING>
    sid = parse_qs(urlparse(frame_location).query)["sid"]
    # Access the frame endpoint with a GET to get form info.
    frame_resp = sess.get(frame_location)
    frame_soup = BeautifulSoup(frame_resp.text, "html.parser")
    tx_value = frame_soup.find('input', {'name': 'tx'})['value']
    akey_value = frame_soup.find('input', {'name': 'akey'})['value']
    xsrf_value = frame_soup.find('input', {'name': '_xsrf'})['value']
    form_data = {
        "tx": tx_value,
        "parent": "None",
        "_xsrf": xsrf_value,
        "version": "v4",
        "akey": akey_value,
        "is_user_verifying_platform_authenticator_available": "false",
    }

    # POST to the endpoint to submit the info we got from GET.
    frame_post_resp = sess.post(frame_location, data=form_data, allow_redirects=False)
    # And we should get redirected to a "prompt" endpoint.
    prompt_location = DUO_ENDPOINT + frame_post_resp.headers["location"]

    # Authenticate with Duo
    auth_resp = sess.post(DUO_ENDPOINT + "/frame/v4/prompt", data={
        "passcode": totp.now(),
        "device": "null",
        "factor": "Passcode",
        "postAuthDestination": "OIDC_EXIT",
        "browser_features": '{"platform_authenticator_status":"available","webauthn_supported":false}',
        "sid": sid,
    })
    # We should now get someting like
    # {
    #   "stat": "OK",
    #   "response": {
    #     "txid": "<SOME_UUID>",
    #     "redirect_to_inline_auth": false
    #   }
    # }
    txid = json.loads(auth_resp.text)["response"]["txid"]

    # Query Duo for the status to ensure we authenticated successfully
    status_resp = sess.post(DUO_ENDPOINT + "/frame/v4/status", data={
        "txid": txid,
        "sid": sid
    })

    duo_result = json.loads(status_resp.text)["response"]
    logger.info(f"Duo returned {duo_result['result']}: {duo_result['reason']}")

    # Record the time when we made the reset request.
    request_timestamp = datetime.now(timezone.utc)
    # This redirects us back to UIUC system and sends the reset email.
    exit_resp = sess.post(DUO_ENDPOINT + "/frame/v4/oidc/exit", data= {
        "txid": txid,
        "sid": sid,
        "factor": "Duo+Mobile+Passcode",
        "device_key": "",
        "_xsrf": xsrf_value,
        "dampen_choice": "true"
    })

    return request_timestamp


def get_reset_url(request_timestamp: datetime) -> str:
    logger.info("Retrieving password reset link from email.")
    # Now retrieve the email.
    mail.login(config.email_account, config.email_password)
    mail.select("inbox")
    mail_content = ""
    while True:
        status, messages = mail.search(None, f'SUBJECT "{EMAIL_SUBJECT}"')
        latest_email_id = messages[0].decode().split(" ")[-1]
        status, latest_email = mail.fetch(latest_email_id, "(RFC822)")

        assert status == 'OK'
        # Get the email content
        msg = email.message_from_bytes(latest_email[0][1])
        # Get the email timestamp.
        email_timestamp = email.utils.parsedate_to_datetime(msg["Date"])
        # Email servers might have small time deltas
        # We only want the email that's more recent than our reset request.
        if email_timestamp > request_timestamp - timedelta(seconds=10):
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    logger.info(f"Got reset link. It was sent at {email_timestamp}")
                    mail_content = part.get_payload()
                    break
            break
        else:
            logger.info(f"Latest password reset email was sent at {email_timestamp}, retrying in 5s.")
        time.sleep(5)

    # Extract the reset credentials URL from the email.
    start_idx = mail_content.find(EMAIL_URL_PREFIX)
    end_idx = start_idx + len(EMAIL_URL_PREFIX)
    next_whitespace_idx = mail_content.find(" ", end_idx)
    reset_url = mail_content[start_idx:next_whitespace_idx]
    return reset_url


def generate_passwd() -> str:
    # Generate a new password and show it.
    chars = [random.choice(string.ascii_uppercase), random.choice(string.ascii_lowercase), random.choice(string.digits), random.choice(ALLOWED_PUNCT), *(random.choice(string.ascii_letters+string.digits+ALLOWED_PUNCT) for _ in range(12))]
    random.shuffle(chars)
    return "".join(chars)


def perform_reset(reset_url: str, new_passwd: str):
    sess = requests.session()
    sess.get(reset_url)
    # Reset your password.
    reset_resp = sess.post(IDSERVER_ENDPOINT + "/setPassword", data={
        "passwd": new_passwd
    })
    reset_result = json.loads(reset_resp.text)
    if type(reset_result) is dict:
        logger.info(f"Reset successful, password valid until {reset_result['expireDate']}.")
    else:
        logger.error(f"Reset failed: {reset_result}")


request_timestamp = request_email()
logger.info(f"Requested password reset email at {request_timestamp}")
reset_url = get_reset_url(request_timestamp)
new_passwd = generate_passwd()
logger.warning(f"Here is your new password! {new_passwd}")
perform_reset(reset_url, new_passwd)
