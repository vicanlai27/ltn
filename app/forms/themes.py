from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField,
    SubmitField, IntegerField, DateTimeLocalField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.models.editorial import Theme


class ThemeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    slug = StringField("Slug", validators=[Optional(), Length(max=140)],
                       description="Auto-generated from name if blank")
    description = TextAreaField("Description", validators=[Optional()])
    theme_type = SelectField("Type", choices=[
        (Theme.TYPE_CALENDAR, "Calendar"),
        (Theme.TYPE_SCHOOL_EVENT, "School Event"),
        (Theme.TYPE_SPECIAL_EDITION, "Special Edition"),
        (Theme.TYPE_EDITORIAL, "Editorial"),
        (Theme.TYPE_MANUAL, "Manual"),
    ], validators=[DataRequired()])

    start_date = DateTimeLocalField("Start Date", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    end_date = DateTimeLocalField("End Date", format="%Y-%m-%dT%H:%M", validators=[Optional()])

    # Colors (hex)
    primary_color = StringField("Primary Color", validators=[Optional(), Length(max=7)],
                                description="Hex code, e.g. #0B3C8C")
    secondary_color = StringField("Secondary Color", validators=[Optional(), Length(max=7)])
    accent_color = StringField("Accent Color", validators=[Optional(), Length(max=7)])
    background_color = StringField("Background Color", validators=[Optional(), Length(max=7)])
    text_color = StringField("Text Color", validators=[Optional(), Length(max=7)])

    # Assets
    header_logo = FileField("Header Logo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp", "svg"])])
    banner_image = FileField("Banner Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    background_image = FileField("Background Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])

    # Decorations (JSON strings for simplicity)
    decoration_motif = SelectField("Decoration Motif", choices=[
        ("", "— None —"),
        ("christmas", "Christmas (bells, ornaments)"),
        ("celebration", "Celebration (confetti)"),
        ("hearts", "Hearts"),
        ("floral", "Floral"),
        ("crescent", "Crescent"),
        ("independence", "Independence"),
        ("books", "Books"),
        ("snow", "Snow"),
    ], validators=[Optional()])
    decoration_density = SelectField("Decoration Density", choices=[
        ("none", "None"),
        ("low", "Low"),
        ("medium", "Medium"),
    ], default="low", validators=[Optional()])

    # Animations
    animation_snow = BooleanField("Snow Animation")
    animation_sparkle = BooleanField("Sparkle Animation")
    animation_float = BooleanField("Floating Elements")

    sound_enabled = BooleanField("Enable Sound Effects")
    is_active = BooleanField("Active", default=True)
    priority = IntegerField("Priority", default=0,
                            description="Higher priority wins. Manual override: 1000")

    submit = SubmitField("Save Theme")