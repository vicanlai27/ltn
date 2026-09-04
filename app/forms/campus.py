from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, IntegerField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.models.sports import Fixture


class HouseForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    logo = FileField("Logo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    color = StringField("Color (hex)", validators=[Optional(), Length(max=7)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class ClubForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    logo = FileField("Logo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    cover_image = FileField("Cover Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    meeting_information = TextAreaField("Meeting Information", validators=[Optional()])
    leader_name = StringField("Leader Name", validators=[Optional(), Length(max=120)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class SportForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    icon = FileField("Icon", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class TeamForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    sport_id = SelectField("Sport", coerce=int, validators=[DataRequired()])
    logo = FileField("Logo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    season = StringField("Season", validators=[Optional(), Length(max=40)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class FixtureForm(FlaskForm):
    home_team_id = SelectField("Home Team", coerce=int, validators=[DataRequired()])
    away_team_id = SelectField("Away Team", coerce=int, validators=[DataRequired()])
    competition = StringField("Competition", validators=[Optional(), Length(max=120)])
    venue = StringField("Venue", validators=[Optional(), Length(max=120)])
    match_date = DateTimeLocalField("Match Date", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    status = SelectField("Status", choices=[
        (Fixture.STATUS_SCHEDULED, "Scheduled"),
        (Fixture.STATUS_LIVE, "Live"),
        (Fixture.STATUS_COMPLETED, "Completed"),
        (Fixture.STATUS_POSTPONED, "Postponed"),
        (Fixture.STATUS_CANCELLED, "Cancelled"),
    ], validators=[DataRequired()])
    home_score = IntegerField("Home Score", validators=[Optional()])
    away_score = IntegerField("Away Score", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


class CampusEventForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    event_type = SelectField("Event Type", choices=[
        ("academic", "Academic"),
        ("sports", "Sports"),
        ("club", "Club"),
        ("cultural", "Cultural"),
        ("assembly", "Assembly"),
    ], validators=[Optional()])
    start_at = DateTimeLocalField("Start", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_at = DateTimeLocalField("End", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    location = StringField("Location", validators=[Optional(), Length(max=255)])
    image = FileField("Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    organizer = StringField("Organizer", validators=[Optional(), Length(max=120)])
    status = SelectField("Status", choices=[
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ], validators=[DataRequired()])
    submit = SubmitField("Save")


class StudentForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    photo = FileField("Photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    class_or_level = StringField("Class/Level", validators=[Optional(), Length(max=60)])
    house_id = SelectField("House", coerce=int, validators=[Optional()])
    achievements = TextAreaField("Achievements", validators=[Optional()])
    bio = TextAreaField("Bio", validators=[Optional()])
    is_featured = BooleanField("Featured")
    submit = SubmitField("Save")


class StaffForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    photo = FileField("Photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    role = StringField("Role", validators=[Optional(), Length(max=120)])
    department = StringField("Department", validators=[Optional(), Length(max=120)])
    bio = TextAreaField("Bio", validators=[Optional()])
    is_featured = BooleanField("Featured")
    submit = SubmitField("Save")


class AlumniForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    graduation_year = IntegerField("Graduation Year", validators=[Optional(), NumberRange(min=1900, max=2100)])
    photo = FileField("Photo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    current_role = StringField("Current Role", validators=[Optional(), Length(max=160)])
    location = StringField("Location", validators=[Optional(), Length(max=120)])
    story = TextAreaField("Story", validators=[Optional()])
    is_featured = BooleanField("Featured")
    submit = SubmitField("Save")