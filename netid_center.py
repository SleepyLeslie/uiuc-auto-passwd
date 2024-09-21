from datetime import datetime, timezone 
import json
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
import pyotp
from logger import logger
from consts import *
from config import Config, AuthConfig


class NetIDCenter:

    def __init__(self, config: Config):
        self.config: AuthConfig = config.netid_config
        self.totp = pyotp.TOTP(self.config.duo_key, interval=30, digits=6)


    def request_email(self) -> datetime:
        logger.info("Preparing to request password reset.")
        sess = requests.session()
        # Set up a session and get a JSESSIONID.
        sess.get(f"{IDSERVER_ENDPOINT}/start")
        # Tell the system our NetID.
        sess.post(f"{IDSERVER_ENDPOINT}/postNetId", data={"netId": self.config.netid})

        logger.info("Starting authentication.")
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
            "passcode": self.totp.now(),
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
        if duo_result["result"] == "SUCCESS":
            logger.info("Duo authentication succeeded.")
        else:
            logger.error(f"Duo authentication failed, please retry. {duo_result['result']}: {duo_result['reason']}")
            exit(1)

        # Record the time when we made the reset request.
        request_timestamp = datetime.now(timezone.utc)
        # This redirects us back to UIUC system and sends the reset email.
        getmail_resp = sess.post(DUO_ENDPOINT + "/frame/v4/oidc/exit", data= {
            "txid": txid,
            "sid": sid,
            "factor": "Duo+Mobile+Passcode",
            "device_key": "",
            "_xsrf": xsrf_value,
            "dampen_choice": "true"
        })

        getmail_soup = BeautifulSoup(getmail_resp.text, "html.parser")
        getmail_opts = json.loads(getmail_soup.find("script").string.split("=")[1].rstrip(";\n"))
        if getmail_opts["pwEmailLocked"]:
            logger.error(f"Your email option has been disabled until {getmail_opts['pwEmailLockedUntil']}")
            exit(1)

        return request_timestamp


    def perform_reset(self, reset_url: str, new_passwd: str) -> bool:
        sess = requests.session()
        sess.get(reset_url)
        # Reset your password.
        reset_resp = sess.post(IDSERVER_ENDPOINT + "/setPassword", data={
            "passwd": new_passwd
        })
        reset_result = json.loads(reset_resp.text)
        if type(reset_result) is dict:
            logger.info(f"Reset successful, password valid until {reset_result['expireDate']}.")
            return True
        else:
            logger.error(f"Reset failed: {reset_result}")
            return False
