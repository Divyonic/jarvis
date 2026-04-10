import sqlite3
from datetime import datetime, date, timedelta
from config import DB_PATH, PRIORITY_MEDIUM, PRIORITY_LABELS


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_at TIMESTAMP,
            priority INTEGER DEFAULT 2,
            recurring TEXT DEFAULT NULL,
            completed INTEGER DEFAULT 0,
            notified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP DEFAULT NULL,
            deleted_at TIMESTAMP DEFAULT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_due_at ON tasks(due_at);
        CREATE INDEX IF NOT EXISTS idx_completed ON tasks(completed);
    """)
    # Add deleted_at column if missing (existing DBs)
    try:
        conn.execute("SELECT deleted_at FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
        conn.commit()
    conn.close()


def add_task(title, due_at=None, priority=PRIORITY_MEDIUM, description="", recurring=None):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description, due_at, priority, recurring) VALUES (?, ?, ?, ?, ?)",
        (title, description, due_at, priority, recurring),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def get_task(task_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_tasks(include_completed=False, today_only=False):
    conn = get_connection()
    query = "SELECT * FROM tasks"
    conditions = ["deleted_at IS NULL"]
    params = []

    if not include_completed:
        conditions.append("completed = 0")

    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        conditions.append("due_at BETWEEN ? AND ?")
        params.extend([today_start.isoformat(), today_end.isoformat()])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY priority DESC, due_at ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_tasks_week():
    """Get tasks for the next 7 days."""
    conn = get_connection()
    today_start = datetime.combine(date.today(), datetime.min.time())
    week_end = datetime.combine(date.today() + timedelta(days=7), datetime.max.time())
    rows = conn.execute(
        "SELECT * FROM tasks WHERE deleted_at IS NULL AND completed = 0 AND due_at BETWEEN ? AND ? ORDER BY due_at ASC, priority DESC",
        (today_start.isoformat(), week_end.isoformat()),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_overdue_tasks():
    """Get tasks that are past due and not completed."""
    conn = get_connection()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE deleted_at IS NULL AND completed = 0 AND due_at < ? AND due_at IS NOT NULL ORDER BY due_at ASC",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_tasks(keyword):
    """Search tasks by keyword in title or description."""
    conn = get_connection()
    pattern = f"%{keyword}%"
    rows = conn.execute(
        "SELECT * FROM tasks WHERE deleted_at IS NULL AND (title LIKE ? OR description LIKE ?) ORDER BY completed ASC, priority DESC, due_at ASC",
        (pattern, pattern),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_next_task():
    """Get the next upcoming task."""
    conn = get_connection()
    now = datetime.now().isoformat()
    row = conn.execute(
        "SELECT * FROM tasks WHERE deleted_at IS NULL AND completed = 0 AND due_at >= ? ORDER BY due_at ASC LIMIT 1",
        (now,),
    ).fetchone()
    if not row:
        # Fall back to any pending task
        row = conn.execute(
            "SELECT * FROM tasks WHERE deleted_at IS NULL AND completed = 0 ORDER BY priority DESC, created_at ASC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    """Get task statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL").fetchone()["cnt"]
    completed = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL AND completed = 1").fetchone()["cnt"]
    pending = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL AND completed = 0").fetchone()["cnt"]
    overdue = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL AND completed = 0 AND due_at < ? AND due_at IS NOT NULL",
        (datetime.now().isoformat(),),
    ).fetchone()["cnt"]

    # Streak: consecutive days with at least one completion
    rows = conn.execute(
        "SELECT DISTINCT DATE(completed_at) as d FROM tasks WHERE deleted_at IS NULL AND completed = 1 AND completed_at IS NOT NULL ORDER BY d DESC"
    ).fetchall()
    streak = 0
    check_date = date.today()
    for row in rows:
        if row["d"] == check_date.isoformat():
            streak += 1
            check_date -= timedelta(days=1)
        elif row["d"] == (check_date - timedelta(days=1)).isoformat():
            check_date = date.fromisoformat(row["d"])
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Busiest day
    busiest = conn.execute(
        "SELECT strftime('%w', due_at) as dow, COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL AND due_at IS NOT NULL GROUP BY dow ORDER BY cnt DESC LIMIT 1"
    ).fetchone()
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    busiest_day = day_names[int(busiest["dow"])] if busiest else "N/A"

    conn.close()
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "streak": streak,
        "busiest_day": busiest_day,
    }


def clear_completed():
    """Permanently remove completed tasks."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE completed = 1 AND deleted_at IS NULL").fetchone()["cnt"]
    conn.execute("UPDATE tasks SET deleted_at = ? WHERE completed = 1 AND deleted_at IS NULL", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()
    return count


def soft_delete_task(task_id):
    """Soft delete a task (can be undone)."""
    conn = get_connection()
    conn.execute("UPDATE tasks SET deleted_at = ? WHERE id = ?", (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()


def undo_last():
    """Restore the most recently deleted or completed task."""
    conn = get_connection()
    # Try to find last soft-deleted task
    row = conn.execute(
        "SELECT * FROM tasks WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT 1"
    ).fetchone()
    if row:
        conn.execute("UPDATE tasks SET deleted_at = NULL WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return dict(row), "restored"

    # Try to find last completed task
    row = conn.execute(
        "SELECT * FROM tasks WHERE completed = 1 ORDER BY completed_at DESC LIMIT 1"
    ).fetchone()
    if row:
        conn.execute("UPDATE tasks SET completed = 0, completed_at = NULL WHERE id = ?", (row["id"],))
        conn.commit()
        conn.close()
        return dict(row), "uncompleted"

    conn.close()
    return None, None


def clean_sheet():
    """Delete all tasks — fresh start."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE deleted_at IS NULL").fetchone()["cnt"]
    conn.execute("UPDATE tasks SET deleted_at = ? WHERE deleted_at IS NULL", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()
    return count


def complete_task(task_id):
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
        (datetime.now().isoformat(), task_id),
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    soft_delete_task(task_id)


def get_due_tasks():
    """Get tasks that are due now and haven't been notified yet."""
    conn = get_connection()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE due_at <= ? AND completed = 0 AND notified = 0 AND deleted_at IS NULL ORDER BY priority DESC",
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notified(task_id):
    conn = get_connection()
    conn.execute("UPDATE tasks SET notified = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_pending_count():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE completed = 0 AND deleted_at IS NULL").fetchone()
    conn.close()
    return row["cnt"]


def update_task(task_id, **kwargs):
    conn = get_connection()
    allowed = {"title", "description", "due_at", "priority", "recurring"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [task_id]
    conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def format_task(task):
    """Format a task dict for display."""
    status = "Done" if task["completed"] else "Pending"
    pri = PRIORITY_LABELS.get(task["priority"], "Medium")
    due = task["due_at"] if task["due_at"] else "No due date"
    recurring = f" (recurring: {task['recurring']})" if task["recurring"] else ""
    return f"[{task['id']}] [{pri}] {task['title']} | Due: {due} | {status}{recurring}"
