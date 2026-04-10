import os

# Ntfy configuration
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "jarvis-wake-me-up")  # Change this to your unique topic
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")

# Database
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

# Scheduler
CHECK_INTERVAL_SECONDS = 30  # How often to check for due tasks
DAILY_DIGEST_HOUR = 7  # Send daily digest at 7 AM
DAILY_DIGEST_MINUTE = 0

# Priority levels
PRIORITY_HIGH = 3
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 1
PRIORITY_LABELS = {1: "Low", 2: "Medium", 3: "High"}
