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
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
NETID = config["general"]["netid"]
IMAP_SERVER = config["email"]["server"]
EMAIL_ACCOUNT = config["email"]["address"]
EMAIL_PASSWORD = config["email"]["password"]

IDSERVER_ENDPOINT = "https://identity.uillinois.edu/iamFrontEnd/iam"
DUO_ENDPOINT = "https://api-cd3ecedb.duosecurity.com"
EMAIL_URL_PREFIX = "https://identity.uillinois.edu/iamFrontEnd/iam/password/reset/email?uin="
ALLOWED_PUNCT = "!#$%&()*+-./:;<=>?[\\]^_`{|}~"
EMAIL_SUBJECT = "University of Illinois - Email Password Reset"

sess = requests.session()
mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)

# get JSESSIONID
sess.get(f"{IDSERVER_ENDPOINT}/start")

# set netid
sess.post(f"{IDSERVER_ENDPOINT}/postNetId", data={"netId": NETID})

# reset password - this would require Duo auth
try_reset_resp = sess.get(f"{IDSERVER_ENDPOINT}/forgottenPWoptions", allow_redirects=False)
# The first attempt should take us to Duo.
assert try_reset_resp.status_code == 302
duo_location = try_reset_resp.headers["location"]
print("DUO LOCATION", duo_location, end="\n\n")
# This URL looks like https://api-cd3ecedb.duosecurity.com/oauth/v1/authorize
#   ?scope=openid
#   &response_type=code
#   &redirect_uri=https://identity.uillinois.edu/iamFrontEnd/iam/authenticationDone
#   &client_id=<SOMETHING>
#   &request=<VERY_LONG_STRING>
# Access the given URL. It returns 303 and redirects us again to a "frame" endpoint.
auth_init_resp = sess.get(duo_location, allow_redirects=False)
frame_location = DUO_ENDPOINT + auth_init_resp.headers["location"]
sid = parse_qs(urlparse(frame_location).query)["sid"]
print("FRAME LOCATION", frame_location, end="\n\n")
# This URL looks like https://api-cd3ecedb.duosecurity.com/frame/frameless/v4/auth
#   ?sid=frameless-<SOME_UUID>
#   &tx=<VERY_LONG_STRING>
#   &req-trace-group=<SOMETHING>

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
    "has_session_trust_analysis_feature": "False",
    "session_trust_extension_id": "",
    "java_version": "",
    "flash_version": "",
    "screen_resolution_width": "1200",
    "screen_resolution_height": "1000",
    "extension_instance_key": "",
    "color_depth": "24",
    "has_touch_capability": "false",
    "ch_ua_error": "",
    "client_hints": "",
    "is_cef_browser": "false",
    "is_ipad_os": "false",
    "is_ie_compatibility_mode": "",
    "is_user_verifying_platform_authenticator_available": "false",
    "user_verifying_platform_authenticator_available_error": "",
    "acting_ie_version": "",
    "react_support": "true",
    "react_support_error_message": ""
}

# POST to the endpoint to tell Duo about your environment : )
frame_post_resp = sess.post(frame_location, data=form_data, allow_redirects=False, headers={
    "Referer": frame_location
})
# And we should get redirected to a "prompt" endpoint.
prompt_location = DUO_ENDPOINT + frame_post_resp.headers["location"]

print("Enter Duo code: ", end="")
duo_code = input()

# Authenticate with Duo
auth_resp = sess.post(DUO_ENDPOINT + "/frame/v4/prompt", data={
    "passcode": duo_code,
    "device": "null",
    "factor": "Passcode",
    "postAuthDestination": "OIDC_EXIT",
    "browser_features": '{"touch_supported":false,"platform_authenticator_status":"available","webauthn_supported":false}',
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

print(status_resp.text)

# Record the time when we made the reset request.
request_timestamp = datetime.now(timezone.utc)
print("REQUESTED", request_timestamp)
# This redirects us back to UIUC system and sends the reset email.
exit_resp = sess.post(DUO_ENDPOINT + "/frame/v4/oidc/exit", data= {
    "txid": txid,
    "sid": sid,
    "factor": "Duo+Mobile+Passcode",
    "device_key": "",
    "_xsrf": xsrf_value,
    "dampen_choice": "true"
})

# Now retrieve the email.
mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
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
    print("LATEST_EMAIL", email_timestamp)
    # Email servers might have small time deltas
    # We only want the email that's more recent than our reset request.
    if email_timestamp > request_timestamp - timedelta(seconds=10):
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                mail_content = part.get_payload()
                break
        break

# Extract the reset credentials URL from the email.
start_idx = mail_content.find(EMAIL_URL_PREFIX)
end_idx = start_idx + len(EMAIL_URL_PREFIX)
next_whitespace_idx = mail_content.find(" ", end_idx)
reset_url = mail_content[start_idx:next_whitespace_idx]
print("RESET_URL", reset_url)

sess2 = requests.session()
sess2.get(reset_url)

# Generate a new password and show it.
chars = [random.choice(string.ascii_uppercase), random.choice(string.ascii_lowercase), random.choice(string.digits), random.choice(ALLOWED_PUNCT), *(random.choice(string.ascii_letters+string.digits+ALLOWED_PUNCT) for _ in range(12))]
random.shuffle(chars)
new_password = "".join(chars)
print("NEW", new_password)

# Reset your password.
reset_resp = sess2.post(IDSERVER_ENDPOINT + "/setPassword", data={
    "passwd": new_password
})
print(reset_resp.text)
