import json
import secrets
import string
from datetime import datetime, timezone

import bcrypt
import pyotp
from flask import current_app, session
from flask_login import login_user, logout_user

from app.extensions import db
from app.models.user import User
from app.services.activity_service import log_activity
from app.utils.security import utcnow


class AuthService:
    """
    Core authentication and account governance logic.
    Enforces: role hierarchy, account verification workflow, 2FA, audit logging.
    """

    @staticmethod
    def create_user(
        creator: User,
        username: str,
        email: str,
        password: str,
        role: str,
        display_name: str = None,
    ) -> User:
        """
        Create a new user account with governance rules:
        - super_admin can create any role
        - admin can create any role EXCEPT admin/super_admin
        - admin-created accounts enter pending_verification
        - super_admin-created accounts are immediately active
        """
        if creator.role not in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
            raise PermissionError("Only an admin or superadmin can create accounts")

        if role not in User.ROLES:
            raise ValueError("Invalid user role")

        # Authorization check
        if creator.role == User.ROLE_ADMIN and role in (User.ROLE_SUPER_ADMIN, User.ROLE_ADMIN):
            raise PermissionError("Admins cannot create admin or super_admin accounts")

        # Determine account status based on creator role
        if creator.role == User.ROLE_SUPER_ADMIN:
            account_status = User.STATUS_ACTIVE
            verified_at = utcnow()
            verified_by_id = creator.id
        else:
            account_status = User.STATUS_PENDING
            verified_at = None
            verified_by_id = None

        user = User(
            username=username,
            email=email,
            role=role,
            account_status=account_status,
            created_by_id=creator.id,
            verified_by_id=verified_by_id,
            verified_at=verified_at,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Create AuthorProfile if user is a content creator role
        if role in (User.ROLE_AUTHOR, User.ROLE_EDITOR, User.ROLE_TEACHER_EDITOR, User.ROLE_STUDENT_JOURNALIST):
            from app.models.user import AuthorProfile
            from app.utils.security import slugify

            profile = AuthorProfile(
                user_id=user.id,
                display_name=display_name or username,
                slug=f"{slugify(display_name or username)}-{user.id}",
            )
            db.session.add(profile)
            db.session.commit()

        # Log activity
        log_activity(
            actor_id=creator.id,
            action="user.create",
            target_type="user",
            target_id=user.id,
            notes=f"Created user {username} with role {role}",
        )

        return user

    @staticmethod
    def verify_account(verifier: User, user_id: int) -> User:
        """
        Verify a pending account (super_admin only).
        Sets account_status to active and records verification metadata.
        """
        if verifier.role != User.ROLE_SUPER_ADMIN:
            raise PermissionError("Only super_admin can verify accounts")

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        if user.account_status != User.STATUS_PENDING:
            raise ValueError("Account is not pending verification")

        user.account_status = User.STATUS_ACTIVE
        user.verified_by_id = verifier.id
        user.verified_at = utcnow()
        db.session.commit()

        log_activity(
            actor_id=verifier.id,
            action="user.verify",
            target_type="user",
            target_id=user.id,
            notes=f"Verified account {user.username}",
        )

        return user

    @staticmethod
    def authenticate(username_or_email: str, password: str) -> tuple[User | None, str]:
        """
        Authenticate a user by username or email + password.
        Returns (user, error_message). If successful, error_message is None.
        Does NOT call login_user() — caller handles that (for 2FA flow).
        """
        user = User.query.filter(
            db.or_(
                User.username == username_or_email,
                User.email == username_or_email,
            )
        ).first()

        if not user:
            return None, "Invalid credentials"

        if not user.check_password(password):
            return None, "Invalid credentials"

        if not user.can_login:
            if user.account_status == User.STATUS_PENDING:
                return None, "Account pending verification"
            elif user.account_status == User.STATUS_SUSPENDED:
                return None, "Account suspended"
            elif user.account_status == User.STATUS_DEACTIVATED:
                return None, "Account deactivated"
            elif not user.is_active:
                return None, "Account inactive"

        return user, None

    @staticmethod
    def complete_login(user: User, remember: bool = False):
        """Complete the login process after password (and 2FA if required) verification."""
        user.last_login_at = utcnow()
        db.session.commit()
        login_user(user, remember=remember)

        log_activity(
            actor_id=user.id,
            action="user.login",
            target_type="user",
            target_id=user.id,
        )

    @staticmethod
    def logout():
        """Log out the current user and clear partial auth state."""
        from flask_login import current_user
        if current_user.is_authenticated:
            log_activity(
                actor_id=current_user.id,
                action="user.logout",
                target_type="user",
                target_id=current_user.id,
            )
        session.pop('partial_auth_user_id', None)
        logout_user()

    # === Two-Factor Authentication ===

    @staticmethod
    def generate_2fa_secret(user: User) -> tuple[str, str, str]:
        """
        Generate a new TOTP secret for 2FA enrollment.
        Returns (secret, provisioning_uri, qr_code_base64).
        """
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="Lavisco News")

        # Generate QR code
        import qrcode
        import base64
        from io import BytesIO

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return secret, uri, qr_base64

    @staticmethod
    def verify_2fa_code(user: User, code: str, secret: str = None) -> bool:
        """
        Verify a TOTP code. If secret is provided, use it (for enrollment verification).
        Otherwise, use the user's stored totp_secret.
        """
        secret_to_use = secret or user.totp_secret
        if not secret_to_use:
            return False

        totp = pyotp.TOTP(secret_to_use)
        return totp.verify(code, valid_window=1)  # Allow 1 step drift (30s window)

    @staticmethod
    def enable_2fa(user: User, secret: str, backup_codes: list[str]):
        """
        Enable 2FA for a user after successful enrollment verification.
        Stores the TOTP secret and hashed backup codes.
        """
        user.totp_secret = secret
        user.totp_enabled = True

        # Hash backup codes
        hashed_codes = [
            bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            for code in backup_codes
        ]
        user.totp_backup_codes_hash = json.dumps(hashed_codes)

        db.session.commit()

        log_activity(
            actor_id=user.id,
            action="user.2fa.enable",
            target_type="user",
            target_id=user.id,
        )

    @staticmethod
    def disable_2fa(user: User):
        """Disable 2FA for a user."""
        user.totp_secret = None
        user.totp_enabled = False
        user.totp_backup_codes_hash = None
        db.session.commit()

        log_activity(
            actor_id=user.id,
            action="user.2fa.disable",
            target_type="user",
            target_id=user.id,
        )

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate random backup codes in XXXX-XXXX format."""
        alphabet = string.ascii_uppercase + string.digits
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes

    @staticmethod
    def verify_backup_code(user: User, code: str) -> bool:
        """
        Verify and consume a backup code. Returns True if valid, False otherwise.
        Valid codes are removed after use (single-use).
        """
        if not user.totp_backup_codes_hash:
            return False

        hashed_codes = json.loads(user.totp_backup_codes_hash)

        for i, hashed in enumerate(hashed_codes):
            try:
                if bcrypt.checkpw(code.encode('utf-8'), hashed.encode('utf-8')):
                    # Remove the used code
                    hashed_codes.pop(i)
                    user.totp_backup_codes_hash = json.dumps(hashed_codes)
                    db.session.commit()

                    log_activity(
                        actor_id=user.id,
                        action="user.2fa.backup_used",
                        target_type="user",
                        target_id=user.id,
                        notes=f"Backup code used. {len(hashed_codes)} remaining.",
                    )
                    return True
            except (ValueError, TypeError):
                continue

        return False


# Convenience instance
auth_service = AuthService()