from datetime import datetime, timedelta
import time
import imaplib
import email
from logger import logger
from consts import *
from config import Config, MailConfig

class ResetURLGetter:

    def __init__(self, config: Config):
        self.config: MailConfig = config.mail_config
        self.mail = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)


    def get(self, request_timestamp: datetime) -> str:
        logger.info("Retrieving password reset link from email.")
        # Now retrieve the email.
        self.mail.login(self.config.email_account, self.config.email_password)
        self.mail.select("inbox")
        mail_content = ""
        while True:
            status, messages = self.mail.search(None, f'SUBJECT "{EMAIL_SUBJECT}"')
            latest_email_id = messages[0].decode().split(" ")[-1]
            status, latest_email = self.mail.fetch(latest_email_id, "(RFC822)")
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
            logger.info(f"Latest password reset email was sent at {email_timestamp}, retrying in 5s.")
            time.sleep(5)

        # Extract the reset credentials URL from the email.
        start_idx = mail_content.find(EMAIL_URL_PREFIX)
        end_idx = start_idx + len(EMAIL_URL_PREFIX)
        next_whitespace_idx = mail_content.find(" ", end_idx)
        reset_url = mail_content[start_idx:next_whitespace_idx]
        return reset_url
