"""Wait for the private MongoDB service before starting each Python process."""
import os
import sys
import time
from pymongo import MongoClient
from pymongo.errors import PyMongoError

client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=2000)
for attempt in range(90):
    try:
        client.admin.command("ping")
        break
    except PyMongoError:
        time.sleep(2)
else:
    raise SystemExit("MongoDB readiness timed out; check the private service")
client.close()
commands = {
    "api": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    "worker": [sys.executable, "-m", "app.worker"],
}
command = commands[sys.argv[1]]
os.execv(command[0], command)
