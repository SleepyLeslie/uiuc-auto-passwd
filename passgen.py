import random
import string
from consts import ALLOWED_PUNCT

def generate_passwd() -> str:
    # Generate a new password and show it.
    chars = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice(ALLOWED_PUNCT),
        *(random.choice(string.ascii_letters+string.digits+ALLOWED_PUNCT) for _ in range(12))
    ]
    random.shuffle(chars)
    return "".join(chars)
