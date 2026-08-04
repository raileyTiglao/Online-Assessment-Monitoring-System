"""
=============================================================================
connection/bootstrap_admin.py — Account Provisioning CLI
Online Assessment Monitoring System
Holy Angel University — School of Computing

Creates Professor/Admin dashboard accounts. There is no self-service
sign-up UI — every account is created here, using the same service-account
credentials the Python monitoring app already uses (connection/
firebase_credentials.json), via the Firebase Admin SDK.

Sets a custom claim (`role: "admin"` or `"professor"`) on the Auth user
AND upserts a matching profile doc in the `users` Firestore collection
(config.py DatabaseConfig.FIRESTORE_USERS_COLLECTION) — the profile doc
exists because the client-side dashboard can't enumerate Auth users
directly, only query Firestore.

IMPORTANT: custom claims only take effect on the user's NEXT ID token
refresh. A freshly created/promoted account must log out and back in (or
the client must force getIdTokenResult(true)) before role-gated dashboard
routes will recognize the new role.

Usage (run as a module, from the repo root, so `config.py` is importable —
running this file directly as a script will fail with
"ModuleNotFoundError: No module named 'config'"):
    py -3.11 -m connection.bootstrap_admin create-admin admin@hau.edu.ph <temp-password>
    py -3.11 -m connection.bootstrap_admin create-professor prof@hau.edu.ph <temp-password> "Dr. Jane Dela Cruz"
    py -3.11 -m connection.bootstrap_admin promote existing@hau.edu.ph admin
=============================================================================
"""

import argparse
import sys
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, auth, firestore

from config import DatabaseConfig

VALID_ROLES = ("admin", "professor")


def init_app() -> None:
    if not firebase_admin._apps:
        cred = credentials.Certificate(DatabaseConfig.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)


def get_or_create_user(email: str, password: str = None, display_name: str = None):
    """Fetch the Auth user by email, creating it if it doesn't exist yet."""
    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        if password is None:
            raise SystemExit(f"[bootstrap_admin] No existing user for {email}, "
                             f"and no password given to create one.")
        kwargs = {"email": email, "password": password, "email_verified": False}
        if display_name:
            kwargs["display_name"] = display_name
        return auth.create_user(**kwargs)


def set_role(user, role: str, created_by: str = "bootstrap-script") -> None:
    """Set the custom claim and upsert the matching users/{uid} profile doc."""
    if role not in VALID_ROLES:
        raise SystemExit(f"[bootstrap_admin] Invalid role '{role}', must be one of {VALID_ROLES}")

    auth.set_custom_user_claims(user.uid, {"role": role})

    db = firestore.client()
    db.collection(DatabaseConfig.FIRESTORE_USERS_COLLECTION).document(user.uid).set({
        "email": user.email,
        "displayName": user.display_name or "",
        "role": role,
        "active": True,
        "createdAt": datetime.now(timezone.utc),
        "createdBy": created_by,
    }, merge=True)

    print(f"[bootstrap_admin] {user.email} (uid={user.uid}) is now role='{role}'. "
          f"They must log out/in before the dashboard recognizes this.")


def cmd_create_admin(args) -> None:
    user = get_or_create_user(args.email, args.password)
    set_role(user, "admin")


def cmd_create_professor(args) -> None:
    user = get_or_create_user(args.email, args.password, args.display_name)
    set_role(user, "professor")


def cmd_promote(args) -> None:
    user = get_or_create_user(args.email)
    set_role(user, args.role)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_admin = subparsers.add_parser("create-admin", help="Create a new Admin account")
    p_admin.add_argument("email")
    p_admin.add_argument("password")
    p_admin.set_defaults(func=cmd_create_admin)

    p_prof = subparsers.add_parser("create-professor", help="Create a new Professor account")
    p_prof.add_argument("email")
    p_prof.add_argument("password")
    p_prof.add_argument("display_name")
    p_prof.set_defaults(func=cmd_create_professor)

    p_promote = subparsers.add_parser("promote", help="Change an existing account's role")
    p_promote.add_argument("email")
    p_promote.add_argument("role", choices=VALID_ROLES)
    p_promote.set_defaults(func=cmd_promote)

    args = parser.parse_args()
    init_app()
    args.func(args)


if __name__ == "__main__":
    main()
