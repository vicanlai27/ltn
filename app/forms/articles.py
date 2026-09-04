from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField,
    SubmitField, DateTimeLocalField, MultipleFileField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.models.content import Article, Category


class ArticleForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    excerpt = TextAreaField("Excerpt", validators=[Optional(), Length(max=500)])
    body = TextAreaField("Body (HTML)", validators=[DataRequired()])
    featured_image = FileField("Featured Image", validators=[
        FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only!")
    ])
    featured_image_alt = StringField("Image Alt Text", validators=[Optional(), Length(max=255)])
    image_caption = StringField("Image Caption", validators=[Optional(), Length(max=255)])
    gallery_images = MultipleFileField("Additional Images", validators=[
        Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Images only!")
    ])
    youtube_video_id = StringField("YouTube Video ID", validators=[Optional()])
    youtube_video_url = StringField("Or paste a YouTube link/ID directly", validators=[Optional()])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    special_edition_id = SelectField("Special Edition", coerce=int, validators=[Optional()])
    content_type = SelectField("Content Type", choices=[
        (Article.TYPE_NEWS, "News Article"),
        (Article.TYPE_OPINION, "Opinion"),
        (Article.TYPE_ANALYSIS, "Analysis"),
        (Article.TYPE_INVESTIGATION, "Investigation"),
        (Article.TYPE_INTERVIEW, "Interview"),
        (Article.TYPE_EXPLAINER, "Explainer"),
        (Article.TYPE_60S, "60 Second Read"),
        (Article.TYPE_BREAKING, "Breaking News"),
        (Article.TYPE_CAMPUS, "Campus Story"),
        (Article.TYPE_SPORTS, "Sports Story"),
    ], validators=[DataRequired()])
    tags = StringField("Tags (comma-separated)", validators=[Optional()])
    audio_file = FileField("Audio Narration", validators=[
        FileAllowed(["mp3", "m4a", "ogg", "wav", "webm"], "Audio files only!")
    ])
    # Campus fields
    is_campus = BooleanField("Campus Story")
    campus_section = SelectField("Campus Section", choices=[
        ("", "— None —"),
        ("campus-news", "Campus News"),
        ("student-life", "Student Life"),
        ("academics", "Academics"),
        ("sports-games", "Sports & Games"),
        ("houses", "Houses"),
        ("clubs-societies", "Clubs & Societies"),
        ("student-spotlight", "Student Spotlight"),
        ("staff-spotlight", "Staff Spotlight"),
        ("campus-pulse", "Campus Pulse"),
        ("campus-calendar", "Campus Calendar"),
        ("campus-gallery", "Campus Gallery"),
        ("campus-shorts", "Campus Shorts"),
        ("student-voice", "Student Voice"),
        ("alumni", "Alumni"),
        ("archive", "School Archive"),
    ], validators=[Optional()])
    house_id = SelectField("House", coerce=int, validators=[Optional()])
    club_id = SelectField("Club", coerce=int, validators=[Optional()])

    # Flags
    is_featured = BooleanField("Featured")
    is_breaking = BooleanField("Breaking News")
    is_editors_pick = BooleanField("Editor's Pick")

    # Scheduling
    publish_at = DateTimeLocalField("Publish At", format="%Y-%m-%dT%H:%M", validators=[Optional()])

    # Poll — optional, attached to this article
    enable_poll = BooleanField("Add a poll to this article")
    poll_question = StringField("Poll Question", validators=[Optional(), Length(max=255)])
    poll_description = StringField("Poll Description (optional)", validators=[Optional(), Length(max=500)])
    poll_allow_multiple = BooleanField("Allow readers to select multiple options")
    poll_option_1 = StringField("Option 1", validators=[Optional(), Length(max=200)])
    poll_option_2 = StringField("Option 2", validators=[Optional(), Length(max=200)])
    poll_option_3 = StringField("Option 3", validators=[Optional(), Length(max=200)])
    poll_option_4 = StringField("Option 4", validators=[Optional(), Length(max=200)])

    submit = SubmitField("Save Draft")
    submit_review = SubmitField("Submit for Review")
    submit_publish = SubmitField("Publish Now")


class CategoryForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional()])
    image = FileField("Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    display_order = StringField("Display Order", default="0")
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class TagForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Save")