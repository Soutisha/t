#!/usr/bin/env python3
"""Verify Twilio API credentials; sending a test SMS requires explicit opt-in."""
import argparse
import os
import re
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send-test-sms", action="store_true",
                        help="send one SMS to the explicitly supplied test number")
    parser.add_argument("--to", help="destination in E.164 format; required with --send-test-sms")
    parser.add_argument("--confirm-send", action="store_true",
                        help="confirm that the one-off test SMS may incur provider charges")
    args = parser.parse_args()

    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    sender = os.getenv("TWILIO_FROM_NUMBER", "")
    if not sid or not token or not sender or "CHANGE_ME" in (sid + token + sender):
        print("ERROR: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER must be configured.", file=sys.stderr)
        return 2

    base = f"https://api.twilio.com/2010-04-01/Accounts/{sid}"
    try:
        check = httpx.get(base + ".json", auth=(sid, token), timeout=httpx.Timeout(10, connect=3))
        check.raise_for_status()
        account = check.json()
    except (httpx.HTTPError, ValueError):
        print("ERROR: Twilio credential check failed. Verify account SID, auth token, account status and network access.", file=sys.stderr)
        return 1
    if not isinstance(account, dict):
        print("ERROR: Twilio returned an unexpected account response.", file=sys.stderr)
        return 1
    account_status = str(account.get("status", "unknown"))
    print(f"Twilio credentials accepted. Account status: {account_status}")
    if account_status.lower() != "active":
        print("ERROR: Twilio account is not active; do not start the pilot.", file=sys.stderr)
        return 1

    if not args.send_test_sms:
        print("No SMS was sent. To send a one-off test, supply --send-test-sms --to +<number> --confirm-send.")
        return 0
    if not args.confirm_send:
        print("ERROR: sending requires --confirm-send because the provider may charge for the SMS.", file=sys.stderr)
        return 2
    if not args.to or not re.fullmatch(r"\+[1-9][0-9]{7,14}", args.to):
        print("ERROR: --to must be a valid E.164 phone number.", file=sys.stderr)
        return 2

    try:
        response = httpx.post(
            base + "/Messages.json",
            data={"To": args.to, "From": sender,
                  "Body": "EUROGRIP PITSTOP OS staging provider verification message."},
            auth=(sid, token),
            timeout=httpx.Timeout(10, connect=3),
        )
        response.raise_for_status()
        message = response.json()
    except (httpx.HTTPError, ValueError):
        print("ERROR: Twilio accepted no verifiable message receipt. Check sender registration, destination and messaging permissions.", file=sys.stderr)
        return 1
    print(f"Test SMS accepted. Message SID: {message.get('sid', 'unknown')}; status: {message.get('status', 'unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
