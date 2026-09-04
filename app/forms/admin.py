from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional

from app.models.user import User


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    role = SelectField('Role', choices=[], validators=[DataRequired()])
    display_name = StringField('Display Name', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Create User')

    def __init__(self, creator_role, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate role choices based on creator's permissions
        if creator_role == User.ROLE_SUPER_ADMIN:
            self.role.choices = [
                (User.ROLE_SUPER_ADMIN, 'Super Admin'),
                (User.ROLE_ADMIN, 'Admin'),
                (User.ROLE_EDITOR, 'Editor'),
                (User.ROLE_TEACHER_EDITOR, 'Teacher Editor'),
                (User.ROLE_AUTHOR, 'Author'),
                (User.ROLE_STUDENT_JOURNALIST, 'Student Journalist'),
                (User.ROLE_STUDENT_CONTRIBUTOR, 'Student Contributor'),
                (User.ROLE_ALUMNI_CONTRIBUTOR, 'Alumni Contributor'),
            ]
        else:  # admin
            self.role.choices = [
                (User.ROLE_EDITOR, 'Editor'),
                (User.ROLE_TEACHER_EDITOR, 'Teacher Editor'),
                (User.ROLE_AUTHOR, 'Author'),
                (User.ROLE_STUDENT_JOURNALIST, 'Student Journalist'),
                (User.ROLE_STUDENT_CONTRIBUTOR, 'Student Contributor'),
                (User.ROLE_ALUMNI_CONTRIBUTOR, 'Alumni Contributor'),
            ]

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already in use')


class EditUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[], validators=[DataRequired()])
    account_status = SelectField('Account Status', choices=[
        (User.STATUS_ACTIVE, 'Active'),
        (User.STATUS_SUSPENDED, 'Suspended'),
        (User.STATUS_DEACTIVATED, 'Deactivated'),
    ], validators=[DataRequired()])
    submit = SubmitField('Update User')

    def __init__(self, editor_role, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if editor_role == User.ROLE_SUPER_ADMIN:
            self.role.choices = [
                (User.ROLE_SUPER_ADMIN, 'Super Admin'),
                (User.ROLE_ADMIN, 'Admin'),
                (User.ROLE_EDITOR, 'Editor'),
                (User.ROLE_TEACHER_EDITOR, 'Teacher Editor'),
                (User.ROLE_AUTHOR, 'Author'),
                (User.ROLE_STUDENT_JOURNALIST, 'Student Journalist'),
                (User.ROLE_STUDENT_CONTRIBUTOR, 'Student Contributor'),
                (User.ROLE_ALUMNI_CONTRIBUTOR, 'Alumni Contributor'),
            ]

        else:  # admin
            self.role.choices = [
                (User.ROLE_EDITOR, 'Editor'),
                (User.ROLE_TEACHER_EDITOR, 'Teacher Editor'),
                (User.ROLE_AUTHOR, 'Author'),
                (User.ROLE_STUDENT_JOURNALIST, 'Student Journalist'),
                (User.ROLE_STUDENT_CONTRIBUTOR, 'Student Contributor'),
                (User.ROLE_ALUMNI_CONTRIBUTOR, 'Alumni Contributor'),
            ]