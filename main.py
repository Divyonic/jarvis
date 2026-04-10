#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", message="urllib3.*OpenSSL")

"""
Jarvis - AI-powered task manager with phone notifications.

Usage:
    jarvis add remind me to call mom at 3pm
    jarvis add buy groceries tomorrow morning urgent
    jarvis add call mom 3pm, buy milk 5pm, gym 7pm
    jarvis list
    jarvis today
    jarvis week
    jarvis next
    jarvis overdue
    jarvis search <keyword>
    jarvis stats
    jarvis done <task_id>
    jarvis delete <task_id>
    jarvis undo
    jarvis edit <task_id> "new title"
    jarvis clear done
    jarvis cleansheet
    jarvis digest
    jarvis run              # Start background scheduler
    jarvis test-notify      # Test ntfy notification
    jarvis test-scheduled   # Test scheduled delivery (1 min delay)
    jarvis motivate         # Random motivational quote
"""

import sys
import random
from datetime import datetime

from database import (
    init_db,
    add_task,
    list_tasks,
    complete_task,
    delete_task,
    format_task,
    get_task,
    update_task,
    get_pending_count,
    mark_notified,
    list_tasks_week,
    list_overdue_tasks,
    search_tasks,
    get_next_task,
    get_stats,
    clear_completed,
    clean_sheet,
    undo_last,
)
from parser import parse_input
from notifier import send_notification, notify_daily_digest, schedule_task_notification
from scheduler import run_scheduler, send_daily_digest
from config import NTFY_TOPIC, PRIORITY_LABELS


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
    "Hardest part is starting. You've already done that by opening Jarvis.",
    "One task at a time. You got this, champion.",
]


def cmd_add(args):
    text = " ".join(args)
    if not text:
        print("Usage: jarvis add \"remind me to call mom at 3pm\"")
        return

    # Batch add: split by comma
    items = [t.strip() for t in text.split(",") if t.strip()]

    for item in items:
        parsed = parse_input(item)
        task_id = add_task(
            title=parsed["title"],
            due_at=parsed["due_at"],
            priority=parsed["priority"],
            recurring=parsed["recurring"],
        )

        print(f"\nTask added (#{task_id}):")
        print(f"  Title:    {parsed['title']}")
        print(f"  Due:      {parsed['due_at'] or 'No due date'}")
        print(f"  Priority: {PRIORITY_LABELS[parsed['priority']]}")
        if parsed["recurring"]:
            print(f"  Recurring: {parsed['recurring']}")

        # Schedule notification on ntfy server
        if parsed["due_at"]:
            success = schedule_task_notification(parsed | {"id": task_id})
            if success:
                mark_notified(task_id)
                print("  Notification scheduled on ntfy server")
            else:
                print("  Warning: Failed to schedule on ntfy. Run 'jarvis run' as fallback.")

    if len(items) > 1:
        print(f"\n{len(items)} tasks added.")


def cmd_list(include_completed=False):
    tasks = list_tasks(include_completed=include_completed)
    if not tasks:
        print("No tasks found.")
        return
    print(f"\n{'All' if include_completed else 'Pending'} Tasks ({len(tasks)}):")
    print("-" * 60)
    for task in tasks:
        print(f"  {format_task(task)}")
    print()


def cmd_today():
    tasks = list_tasks(today_only=True)
    if not tasks:
        print("No tasks due today. You're free!")
        return
    print(f"\nToday's Tasks ({len(tasks)}):")
    print("-" * 60)
    for task in tasks:
        print(f"  {format_task(task)}")
    print()


def cmd_week():
    tasks = list_tasks_week()
    if not tasks:
        print("No tasks for the next 7 days.")
        return
    print(f"\nThis Week's Tasks ({len(tasks)}):")
    print("-" * 60)
    current_day = None
    for task in tasks:
        if task["due_at"]:
            try:
                day = datetime.fromisoformat(task["due_at"]).strftime("%A, %b %d")
            except (ValueError, TypeError):
                day = "Unknown"
        else:
            day = "No date"
        if day != current_day:
            current_day = day
            print(f"\n  {day}:")
        print(f"    {format_task(task)}")
    print()


def cmd_next():
    task = get_next_task()
    if not task:
        print("No upcoming tasks.")
        return
    print(f"\nNext up:")
    print(f"  {format_task(task)}")
    print()


def cmd_overdue():
    tasks = list_overdue_tasks()
    if not tasks:
        print("No overdue tasks. You're on track!")
        return
    print(f"\nOverdue Tasks ({len(tasks)}):")
    print("-" * 60)
    for task in tasks:
        print(f"  {format_task(task)}")
    print()


def cmd_search(args):
    if not args:
        print("Usage: jarvis search <keyword>")
        return
    keyword = " ".join(args)
    tasks = search_tasks(keyword)
    if not tasks:
        print(f"No tasks matching \"{keyword}\".")
        return
    print(f"\nSearch results for \"{keyword}\" ({len(tasks)}):")
    print("-" * 60)
    for task in tasks:
        print(f"  {format_task(task)}")
    print()


def cmd_stats():
    stats = get_stats()
    print(f"\nJarvis Stats:")
    print("-" * 40)
    print(f"  Total tasks:     {stats['total']}")
    print(f"  Completed:       {stats['completed']}")
    print(f"  Pending:         {stats['pending']}")
    print(f"  Overdue:         {stats['overdue']}")
    print(f"  Current streak:  {stats['streak']} day(s)")
    print(f"  Busiest day:     {stats['busiest_day']}")
    if stats['pending'] > 0:
        print(f"\n  {random.choice(MOTIVATIONAL_QUOTES)}")
    print()


def cmd_done(args):
    if not args:
        print("Usage: jarvis done <task_id>")
        return
    task_id = int(args[0])
    task = get_task(task_id)
    if not task:
        print(f"Task #{task_id} not found.")
        return
    complete_task(task_id)
    print(f"Completed: {task['title']}")


def cmd_delete(args):
    if not args:
        print("Usage: jarvis delete <task_id>")
        return
    task_id = int(args[0])
    task = get_task(task_id)
    if not task:
        print(f"Task #{task_id} not found.")
        return
    delete_task(task_id)
    print(f"Deleted: {task['title']} (use 'jarvis undo' to restore)")


def cmd_undo():
    task, action = undo_last()
    if not task:
        print("Nothing to undo.")
        return
    if action == "restored":
        print(f"Restored: {task['title']}")
    elif action == "uncompleted":
        print(f"Uncompleted: {task['title']} (back to pending)")


def cmd_clear_done():
    count = clear_completed()
    if count == 0:
        print("No completed tasks to clear.")
    else:
        print(f"Cleared {count} completed task(s).")


def cmd_cleansheet():
    count = clean_sheet()
    if count == 0:
        print("Already clean. No tasks to delete.")
    else:
        print(f"Wiped {count} task(s). Clean sheet. (use 'jarvis undo' to restore last one)")


def cmd_edit(args):
    if len(args) < 2:
        print("Usage: jarvis edit <task_id> \"new title\"")
        return
    task_id = int(args[0])
    new_text = " ".join(args[1:])
    parsed = parse_input(new_text)
    updates = {"title": parsed["title"]}
    if parsed["due_at"]:
        updates["due_at"] = parsed["due_at"]
    updates["priority"] = parsed["priority"]
    if parsed["recurring"]:
        updates["recurring"] = parsed["recurring"]
    update_task(task_id, **updates)
    print(f"Updated task #{task_id}")

    # Reschedule on ntfy if due date changed
    if parsed["due_at"]:
        task = get_task(task_id)
        if task:
            success = schedule_task_notification(task)
            if success:
                mark_notified(task_id)
                print(f"  Notification rescheduled on ntfy server")


def cmd_test_notify():
    print(f"Sending test notification to topic: {NTFY_TOPIC}")
    success = send_notification(
        "Jarvis Test",
        "If you see this, notifications are working!",
        priority=2,
        tags=["white_check_mark"],
    )
    if success:
        print("Notification sent! Check your phone.")
    else:
        print("Failed to send notification. Check your ntfy setup.")


def cmd_test_scheduled():
    """Send a test notification scheduled 1 minute from now."""
    from datetime import timedelta
    deliver_time = datetime.now() + timedelta(minutes=1)
    print(f"Scheduling test notification for {deliver_time.strftime('%H:%M:%S')} (1 minute from now)...")
    success = send_notification(
        "Jarvis Scheduled Test",
        "This was scheduled 1 minute ago. If you see this, scheduled delivery works!",
        priority=2,
        tags=["white_check_mark", "alarm_clock"],
        deliver_at=deliver_time.isoformat(),
    )
    if success:
        print("Scheduled! You should get a notification in ~1 minute.")
        print("You can close your terminal — ntfy's server will deliver it.")
    else:
        print("Failed to schedule. Check your ntfy setup.")


def cmd_open_up():
    pending = get_pending_count()
    print(f"""
    Jarvis - AI Task Manager
    ========================

    Tasks:
      add <task>              Add a task (e.g. jarvis add call mom at 3pm)
      add <t1>, <t2>, <t3>   Batch add tasks separated by commas
      list                    Show all pending tasks
      list --all              Show all tasks including completed
      today                   Show today's tasks
      week                    Show tasks for the next 7 days
      next                    Show the next upcoming task
      overdue                 Show past-due tasks
      search <keyword>        Find tasks by keyword
      done <id>               Mark a task as completed
      delete <id>             Delete a task
      edit <id> <new text>    Edit a task
      undo                    Restore last deleted/completed task

    Utilities:
      stats                   Show completion stats & streak
      digest                  Send daily digest now
      motivate                Get a motivational quote
      cleansheet              Wipe all tasks — fresh start
      clear done              Purge completed tasks
      test-notify             Test ntfy notification
      test-scheduled          Test scheduled delivery (1 min)
      run                     Start background scheduler
      open up                 Show this menu

    Shortcuts:
      jarvis add <anything>          No quotes needed
      wake up jarvis <command>       Works too
      hey jarvis / yo jarvis         Any prefix works

    You have {pending} pending task(s).
    """)


def cmd_motivate():
    print(f"\n  {random.choice(MOTIVATIONAL_QUOTES)}\n")


def cmd_digest():
    send_daily_digest()


def main():
    init_db()

    if len(sys.argv) < 2:
        print(__doc__)
        count = get_pending_count()
        print(f"You have {count} pending task(s).")
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    # Handle "open up" command
    if command == "open" and args and args[0].lower() == "up":
        cmd_open_up()
        return

    # Handle "clear done" as two-word command
    if command == "clear" and args and args[0].lower() == "done":
        cmd_clear_done()
        return

    commands = {
        "add": lambda: cmd_add(args),
        "list": lambda: cmd_list(include_completed="--all" in args),
        "today": cmd_today,
        "week": cmd_week,
        "next": cmd_next,
        "overdue": cmd_overdue,
        "search": lambda: cmd_search(args),
        "stats": cmd_stats,
        "done": lambda: cmd_done(args),
        "delete": lambda: cmd_delete(args),
        "undo": cmd_undo,
        "cleansheet": cmd_cleansheet,
        "edit": lambda: cmd_edit(args),
        "digest": cmd_digest,
        "run": run_scheduler,
        "test-notify": cmd_test_notify,
        "test-scheduled": cmd_test_scheduled,
        "motivate": cmd_motivate,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print("Please use a command sir. Example: jarvis add remind me of lunch at 2:30pm")
        print("Type 'jarvis' to see all commands.")


if __name__ == "__main__":
    main()
