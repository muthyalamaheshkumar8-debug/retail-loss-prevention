"""Generate local secrets; never commit the resulting .env."""

import secrets
from pathlib import Path
from getpass import getpass

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    raise SystemExit(".env already exists; edit it locally instead of overwriting it.")
email = input("Administrator email: ").strip()
if "@" not in email or "\n" in email or "\r" in email:
    raise SystemExit("Enter a valid email address")
password = getpass("Administrator password (12+ characters, letters/numbers/symbols): ")
if len(password) < 12 or any(c in password for c in ["\n", "\r", "'", "\\"]):
    raise SystemExit(
        "Use 12+ characters without single quotes, backslashes, or newlines."
    )
text = (root / ".env.example").read_text()
text = (
    text.replace("replace-with-at-least-32-random-characters", secrets.token_hex(32))
    .replace("admin@example.com", email)
    .replace("replace-with-a-strong-password", "'" + password + "'")
)
path.write_text(text, encoding="utf-8")
print("Created .env. Start with: docker compose up --build -d")
