"""Grant administrator access to an existing local/staging account.

Run from backend/:
  python scripts/bootstrap_admin.py --phone +91XXXXXXXXXX --confirm GRANT-ADMIN

The account must already have completed OTP verification and mechanic registration.
This command never creates accounts, bypasses OTP, or exposes an HTTP privilege-escalation route.
"""
import argparse
import os
import re
import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import User, UserRole, UserStatus


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant local administrator access to an existing account.")
    parser.add_argument("--phone", required=True, help="Existing account phone number in E.164 format")
    parser.add_argument("--confirm", required=True, help="Must be exactly GRANT-ADMIN")
    args = parser.parse_args()

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "dev", "staging"}:
        print("Refusing to run outside development/staging.", file=sys.stderr)
        return 2
    if args.confirm != "GRANT-ADMIN":
        print("Confirmation did not match. No changes made.", file=sys.stderr)
        return 2
    if not re.fullmatch(r"\+[1-9]\d{7,14}", args.phone):
        print("Phone number must use E.164 format.", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone_e164 == args.phone))
        if user is None:
            print("No account exists. Register and verify the number through the normal OTP flow first.", file=sys.stderr)
            return 1
        if user.status != UserStatus.active:
            print("The account is not active. No role was granted.", file=sys.stderr)
            return 1
        existing = db.scalar(select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_code == "administrator",
            UserRole.scope_type == "global",
            UserRole.scope_id == "*",
        ))
        if existing:
            print(f"Administrator role already exists for {user.display_name} ({user.phone_e164}).")
            return 0
        db.add(UserRole(user_id=user.id, role_code="administrator", scope_type="global", scope_id="*"))
        db.commit()
        print(f"Granted global administrator role to {user.display_name} ({user.phone_e164}).")
        print("Sign out, request a fresh OTP, and sign in again to receive a JWT containing the new role.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
