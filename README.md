# Jarvis

A personal AI task agent that turns natural-language reminders into scheduled push notifications. Built for self-hosting on macOS.

## Features

- **Natural-language task input** — "remind me to call mom tomorrow at 6pm" becomes a scheduled task
- **Push notifications via [ntfy](https://ntfy.sh)** — get alerts on phone, desktop, or any subscribed device
- **Priority levels** — Low / Medium / High
- **Daily morning digest** — every day at 7am, a summary of what's due
- **Recurring motivational pings** — scheduled affirmations via launchd
- **SQLite-backed** — lightweight, file-based, no external services
- **Runs as a launchd agent** — starts on login, runs in the background

## Stack

- Python 3
- SQLite (via `sqlite3` stdlib)
- ntfy.sh for push delivery
- macOS launchd for background execution

## Installation

```bash
git clone git@github.com:Divyonic/jarvis.git
cd jarvis
pip install -r requirements.txt
```

## Configuration

Set your ntfy topic via environment variable (or edit `config.py`):

```bash
export NTFY_TOPIC="your-unique-topic-name"
export NTFY_SERVER="https://ntfy.sh"
```

Subscribe to the same topic from the [ntfy mobile app](https://ntfy.sh/app) or any HTTP client.

## Usage

Run the agent:

```bash
python main.py
```

### Run on login (macOS)

Copy the launchd plists into `~/Library/LaunchAgents/` and load them:

```bash
cp com.drexon.jarvis.plist ~/Library/LaunchAgents/
cp com.drexon.jarvis.motivate.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.drexon.jarvis.plist
launchctl load ~/Library/LaunchAgents/com.drexon.jarvis.motivate.plist
```

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | Entry point and command loop |
| `parser.py` | Natural-language task parsing |
| `scheduler.py` | Due-task polling and dispatch |
| `notifier.py` | ntfy push delivery |
| `database.py` | SQLite task store |
| `config.py` | Runtime configuration |
| `motivate.py` | Recurring motivational notifications |

## License

MIT

---

Built by [Drexon Industries](https://github.com/Divyonic).
