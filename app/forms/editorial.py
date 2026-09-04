from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, IntegerField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional

from app.models.editorial import Theme, SiteAnnouncement


class ThemeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
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
    primary_color = StringField("Primary Color", validators=[Optional(), Length(max=7)])
    secondary_color = StringField("Secondary Color", validators=[Optional(), Length(max=7)])
    accent_color = StringField("Accent Color", validators=[Optional(), Length(max=7)])
    background_color = StringField("Background Color", validators=[Optional(), Length(max=7)])
    text_color = StringField("Text Color", validators=[Optional(), Length(max=7)])
    header_logo = FileField("Header Logo", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    banner_image = FileField("Banner Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    background_image = FileField("Background Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    is_active = BooleanField("Active", default=True)
    priority = IntegerField("Priority", default=0)
    submit = SubmitField("Save")


class AnnouncementForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    message = TextAreaField("Message", validators=[DataRequired()])
    display_type = SelectField("Display Type", choices=[
        (SiteAnnouncement.DISPLAY_BANNER, "Top Banner"),
        (SiteAnnouncement.DISPLAY_MODAL, "Modal Popup"),
        (SiteAnnouncement.DISPLAY_SLIDE, "Slide In"),
    ], validators=[DataRequired()])
    severity = SelectField("Severity", choices=[
        (SiteAnnouncement.SEVERITY_INFO, "Info"),
        (SiteAnnouncement.SEVERITY_SUCCESS, "Success"),
        (SiteAnnouncement.SEVERITY_WARNING, "Warning"),
        (SiteAnnouncement.SEVERITY_URGENT, "Urgent"),
    ], validators=[DataRequired()])
    target_scope = SelectField("Target Scope", choices=[
        (SiteAnnouncement.SCOPE_SITE, "Site Wide"),
        (SiteAnnouncement.SCOPE_CAMPUS, "Campus Only"),
        (SiteAnnouncement.SCOPE_HOME, "Homepage Only"),
    ], validators=[DataRequired()])
    cta_text = StringField("CTA Text", validators=[Optional(), Length(max=80)])
    cta_url = StringField("CTA URL", validators=[Optional(), Length(max=500)])
    dismissible = BooleanField("Dismissible", default=True)
    priority = IntegerField("Priority", default=0)
    start_at = DateTimeLocalField("Start", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    end_at = DateTimeLocalField("End", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class PlacementForm(FlaskForm):
    zone = SelectField("Zone", choices=[
        ("hero_primary", "Hero Primary"),
        ("hero_secondary", "Hero Secondary"),
        ("trending_now", "Trending Now"),
        ("campus_highlights", "Campus Highlights"),
        ("editors_choice", "Editors' Choice"),
        ("special_edition_banner", "Special Edition Banner"),
    ], validators=[DataRequired()])
    article_id = SelectField("Article", coerce=int, validators=[DataRequired()])
    position = IntegerField("Position", default=0)
    is_manual_override = BooleanField("Manual Override (pin)")
    start_at = DateTimeLocalField("Start", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    end_at = DateTimeLocalField("End", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Save")


class AdvertisementForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    placement = SelectField("Placement", choices=[
        ("header", "Header"),
        ("after_hero", "After Hero"),
        ("between_sections", "Between Sections"),
        ("article_top", "Article Top"),
        ("article_middle", "Article Middle"),
        ("article_bottom", "Article Bottom"),
        ("sidebar", "Sidebar"),
        ("campus_page", "Campus Page"),
    ], validators=[DataRequired()])
    image = FileField("Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    html_code = TextAreaField("HTML Code", validators=[Optional()])
    target_url = StringField("Target URL", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Active", default=True)
    start_at = DateTimeLocalField("Start", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    end_at = DateTimeLocalField("End", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    priority = IntegerField("Priority", default=0)
    submit = SubmitField("Save")


class SiteSettingForm(FlaskForm):
    key = StringField("Key", validators=[DataRequired(), Length(max=120)])
    value = TextAreaField("Value", validators=[Optional()])
    submit = SubmitField("Save")
class SpecialEditionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[Optional(), Length(max=280)])
    description = TextAreaField("Description", validators=[Optional()])
    cover_image = FileField("Cover Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    theme_id = SelectField("Theme", coerce=int, validators=[Optional()])
    start_at = DateTimeLocalField("Start", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    end_at = DateTimeLocalField("End", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Edition")
