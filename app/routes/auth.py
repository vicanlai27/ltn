from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import current_user, login_required

from app.extensions import db, limiter
from app.forms.auth import (
    LoginForm, ProfileForm, ChangePasswordForm,
    TwoFactorSetupForm, TwoFactorVerifyForm, TwoFactorBackupForm,
)
from app.models.user import User, AuthorProfile
from app.services.auth_service import auth_service
from app.utils.security import slugify

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _post_login_redirect(user: User, next_page: str | None = None) -> str:
    """Send every user to the workspace they manage.

    A `next` page (e.g. a login triggered by @login_required on some other
    page) still wins. Otherwise: editor-and-above go to the staff admin
    console; everyone else (teacher_editor, author, student_journalist,
    student_contributor, alumni_contributor) goes to their newsroom
    dashboard so they always land somewhere useful, never the homepage.
    """
    if next_page:
        return next_page
    if user.is_at_least(User.ROLE_EDITOR):
        return url_for("admin.dashboard")
    return url_for("newsroom.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user, error = auth_service.authenticate(form.username.data, form.password.data)

        if error:
            flash(error, "error")
            return render_template("auth/login.html", form=form)

        # Check if 2FA is required
        if user.requires_2fa:
            session['partial_auth_user_id'] = user.id
            session['remember_me'] = form.remember.data
            return redirect(url_for("auth.two_factor_verify"))

        # No 2FA — complete login
        auth_service.complete_login(user, remember=form.remember.data)
        next_page = request.args.get('next')
        return redirect(_post_login_redirect(user, next_page))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/2fa/verify", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def two_factor_verify():
    """Second step of login for users with 2FA enabled."""
    user_id = session.get('partial_auth_user_id')
    if not user_id:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if not user:
        session.pop('partial_auth_user_id', None)
        return redirect(url_for("auth.login"))

    form = TwoFactorVerifyForm()
    backup_form = TwoFactorBackupForm()

    if form.validate_on_submit():
        if auth_service.verify_2fa_code(user, form.code.data):
            session.pop('partial_auth_user_id', None)
            remember = session.pop('remember_me', False)
            auth_service.complete_login(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(_post_login_redirect(user, next_page))
        else:
            flash("Invalid 2FA code", "error")

    if backup_form.validate_on_submit():
        if auth_service.verify_backup_code(user, backup_form.backup_code.data):
            session.pop('partial_auth_user_id', None)
            remember = session.pop('remember_me', False)
            auth_service.complete_login(user, remember=remember)
            flash("Backup code used. Please generate new backup codes from your profile.", "warning")
            next_page = request.args.get('next')
            return redirect(_post_login_redirect(user, next_page))
        else:
            flash("Invalid backup code", "error")

    return render_template("auth/2fa_verify.html", form=form, backup_form=backup_form, user=user)


@auth_bp.route("/logout")
@login_required
def logout():
    auth_service.logout()
    flash("You have been logged out", "info")
    return redirect(url_for("public.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(current_user)
    password_form = ChangePasswordForm()

    if form.validate_on_submit():
        current_user.email = form.email.data
        if current_user.author_profile:
            current_user.author_profile.display_name = form.display_name.data
            current_user.author_profile.slug = slugify(form.display_name.data)
        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for("auth.profile"))

    return render_template(
        "auth/profile.html",
        form=form,
        password_form=password_form,
    )


@auth_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect", "error")
            return redirect(url_for("auth.profile"))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Password changed successfully", "success")
        return redirect(url_for("auth.profile"))

    flash("Password change failed. Please check the form.", "error")
    return redirect(url_for("auth.profile"))


@auth_bp.route("/2fa/setup", methods=["GET", "POST"])
@login_required
def two_factor_setup():
    """Enroll in 2FA: generate secret, show QR code, verify code to enable."""
    if current_user.totp_enabled:
        flash("2FA is already enabled", "info")
        return redirect(url_for("auth.profile"))

    # Generate secret and QR code (stored in session for verification)
    secret, uri, qr_base64 = auth_service.generate_2fa_secret(current_user)
    session['2fa_setup_secret'] = secret

    form = TwoFactorSetupForm()
    if form.validate_on_submit():
        setup_secret = session.get('2fa_setup_secret')
        if not setup_secret:
            flash("Setup session expired. Please try again.", "error")
            return redirect(url_for("auth.two_factor_setup"))

        if auth_service.verify_2fa_code(current_user, form.code.data, secret=setup_secret):
            backup_codes = auth_service.generate_backup_codes()
            auth_service.enable_2fa(current_user, setup_secret, backup_codes)
            session.pop('2fa_setup_secret', None)
            flash("2FA enabled successfully. Save your backup codes!", "success")
            return render_template("auth/2fa_backup_codes.html", backup_codes=backup_codes)
        else:
            flash("Invalid code. Please try again.", "error")

    return render_template("auth/2fa_setup.html", form=form, qr_base64=qr_base64, secret=secret)


@auth_bp.route("/2fa/disable", methods=["POST"])
@login_required
def two_factor_disable():
    """Disable 2FA for the current user."""
    if not current_user.totp_enabled:
        flash("2FA is not enabled", "info")
        return redirect(url_for("auth.profile"))

    auth_service.disable_2fa(current_user)
    flash("2FA disabled", "success")
    return redirect(url_for("auth.profile"))