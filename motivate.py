#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", message="urllib3.*OpenSSL")

from notifier import send_motivational_quote

if send_motivational_quote():
    print("Motivational quote sent!")
else:
    print("Failed to send quote.")
