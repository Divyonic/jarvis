import random
import requests
from config import NTFY_SERVER, NTFY_TOPIC, PRIORITY_LABELS

MOTIVATIONAL_QUOTES = [
    "The secret of getting ahead is getting started. — Mark Twain",
    "It always seems impossible until it's done. — Nelson Mandela",
    "Done is better than perfect. — Sheryl Sandberg",
    "Small progress is still progress.",
    "You don't have to be great to start, but you have to start to be great. — Zig Ziglar",
    "Focus on being productive instead of busy. — Tim Ferriss",
    "The way to get started is to quit talking and begin doing. — Walt Disney",
    "Action is the foundational key to all success. — Pablo Picasso",
    "Your future is created by what you do today, not tomorrow. — Robert Kiyosaki",
    "Don't watch the clock; do what it does. Keep going. — Sam Levenson",
    "Discipline is choosing between what you want now and what you want most. — Abraham Lincoln",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "You are never too old to set another goal or to dream a new dream. — C.S. Lewis",
    "Hardest part is starting. You've already done that.",
    "One task at a time. You got this, champion.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill",
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
    "What you do today can improve all your tomorrows. — Ralph Marston",
    "Push yourself, because no one else is going to do it for you.",
]


def send_motivational_quote():
    """Send a random motivational quote as a notification."""
    quote = random.choice(MOTIVATIONAL_QUOTES)
    return send_notification(
        "Jarvis says...",
        quote,
        priority=1,
        tags=["muscle", "star"],
    )


def send_notification(title, message, priority=2, tags=None, deliver_at=None):
    """Send a push notification via ntfy.sh.

    If deliver_at is provided (ISO datetime string), ntfy will hold the
    message server-side and deliver it at that time — even if your Mac is off.
    """
    ntfy_priority_map = {1: 2, 2: 3, 3: 5}
    ntfy_priority = ntfy_priority_map.get(priority, 3)

    headers = {
        "Title": title,
        "Priority": str(ntfy_priority),
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if deliver_at:
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(deliver_at)
            headers["X-At"] = str(int(dt.timestamp()))
        except (ValueError, TypeError):
            headers["X-At"] = deliver_at

    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    try:
        resp = requests.post(url, data=message.encode("utf-8"), headers=headers)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Notification failed: {e}")
        return False


def schedule_task_notification(task):
    """Schedule a notification on ntfy's server for the task's due time."""
    pri_label = PRIORITY_LABELS.get(task["priority"], "Medium")
    tags = ["alarm_clock"]
    if task["priority"] == 3:
        tags.append("exclamation")

    title = f"Jarvis: {task['title']}"
    message = f"Priority: {pri_label}"
    if task.get("description"):
        message += f"\n{task['description']}"

    return send_notification(
        title, message, priority=task["priority"], tags=tags, deliver_at=task["due_at"]
    )


def notify_task_due(task):
    """Send notification for a due task (immediate)."""
    pri_label = PRIORITY_LABELS.get(task["priority"], "Medium")
    tags = ["alarm_clock"]
    if task["priority"] == 3:
        tags.append("exclamation")

    title = f"Jarvis: {task['title']}"
    message = f"Priority: {pri_label}"
    if task.get("description"):
        message += f"\n{task['description']}"

    return send_notification(title, message, priority=task["priority"], tags=tags)


def notify_daily_digest(tasks, completed_count):
    """Send the daily summary digest."""
    if not tasks and completed_count == 0:
        return send_notification(
            "Daily Digest",
            "No tasks for today. Enjoy your day!",
            priority=1,
            tags=["sunrise"],
        )

    lines = [f"Pending tasks: {len(tasks)} | Completed yesterday: {completed_count}", ""]

    for task in tasks:
        pri = PRIORITY_LABELS.get(task["priority"], "M")
        due = task["due_at"][:16] if task["due_at"] else "No time set"
        lines.append(f"[{pri[0]}] {task['title']} - {due}")

    return send_notification(
        "Daily Digest - Your Tasks",
        "\n".join(lines),
        priority=2,
        tags=["sunrise", "memo"],
    )
