import time
import signal
import sys
from datetime import datetime, timedelta, date
import schedule

from config import CHECK_INTERVAL_SECONDS, DAILY_DIGEST_HOUR, DAILY_DIGEST_MINUTE
from database import init_db, get_due_tasks, mark_notified, list_tasks, get_connection
from notifier import notify_task_due, notify_daily_digest


running = True


def handle_signal(signum, frame):
    global running
    print("\nShutting down scheduler...")
    running = False


def check_due_tasks():
    """Check for tasks that are due and send notifications."""
    due_tasks = get_due_tasks()
    for task in due_tasks:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Notifying: {task['title']}")
        success = notify_task_due(task)
        if success:
            mark_notified(task["id"])


def send_daily_digest():
    """Send a daily digest of today's tasks."""
    today_tasks = list_tasks(today_only=True)
    all_pending = list_tasks()

    # Count tasks completed yesterday
    conn = get_connection()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today_str = date.today().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE completed = 1 AND completed_at BETWEEN ? AND ?",
        (yesterday, today_str),
    ).fetchone()
    conn.close()
    completed_yesterday = row["cnt"]

    # Combine today's tasks with any pending tasks that have no date
    digest_tasks = today_tasks or all_pending[:10]
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending daily digest ({len(digest_tasks)} tasks)")
    notify_daily_digest(digest_tasks, completed_yesterday)


def run_scheduler():
    """Main scheduler loop."""
    init_db()
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Schedule daily digest
    digest_time = f"{DAILY_DIGEST_HOUR:02d}:{DAILY_DIGEST_MINUTE:02d}"
    schedule.every().day.at(digest_time).do(send_daily_digest)
    print(f"Jarvis - Scheduler started")
    print(f"  Checking for due tasks every {CHECK_INTERVAL_SECONDS}s")
    print(f"  Daily digest at {digest_time}")
    print(f"  Press Ctrl+C to stop\n")

    last_check = 0
    while running:
        now = time.time()
        if now - last_check >= CHECK_INTERVAL_SECONDS:
            check_due_tasks()
            last_check = now

        schedule.run_pending()
        time.sleep(1)

    print("Scheduler stopped.")


if __name__ == "__main__":
    run_scheduler()
