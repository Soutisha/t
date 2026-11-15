"""Create or promote a platform administrator. Run manually by an authorised operator.

Example:
  python -m scripts.bootstrap_admin +919876543210 "Platform Admin"

The account must already exist, normally after the phone has completed OTP
verification and mechanic registration. This script never creates a password
or bypasses OTP; future sign-ins still use the OTP flow.
"""
import argparse
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import User, UserRole, UserStatus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phone_e164")
    parser.add_argument("display_name")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.phone_e164 == args.phone_e164))
        if not user:
            raise SystemExit("No account exists for this phone. Complete the approved account onboarding first.")
        if user.status != UserStatus.active:
            raise SystemExit("Account is not active; resolve account status before granting admin role.")
        existing = db.scalar(select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_code == "administrator",
            UserRole.scope_type == "global",
            UserRole.scope_id == "*",
        ))
        if not existing:
            db.add(UserRole(user_id=user.id, role_code="administrator", scope_type="global", scope_id="*"))
            db.commit()
        print(f"Administrator role ensured for {user.display_name} ({user.phone_e164}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
