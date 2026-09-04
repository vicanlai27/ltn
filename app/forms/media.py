from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField, SubmitField,
    IntegerField, DateTimeLocalField, MultipleFileField,
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange

# MultipleFileField comes from plain WTForms (not flask_wtf.file) — Flask-WTF's
# FileAllowed validator isn't guaranteed to support list data across versions,
# so extension/size checks for the multi-image field are done in the route
# handler via app.services.media_service.save_upload instead.


class GalleryForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    cover_image = FileField("Cover Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    event_id = SelectField("Linked Campus Event", coerce=int, validators=[Optional()])
    images = MultipleFileField("Add Images", validators=[Optional()])
    published_at = DateTimeLocalField("Publish At", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Save")


class GalleryImageForm(FlaskForm):
    alt_text = StringField("Alt Text", validators=[Optional(), Length(max=255)])
    caption = StringField("Caption", validators=[Optional(), Length(max=255)])
    display_order = IntegerField("Display Order", validators=[Optional()], default=0)
    submit = SubmitField("Save")


class VideoForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    thumbnail = FileField("Thumbnail", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    video_file = FileField("Video File", validators=[FileAllowed(["mp4", "webm"])])
    duration = IntegerField("Duration (seconds)", validators=[Optional(), NumberRange(min=0)])
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    published_at = DateTimeLocalField("Publish At", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Save")


class PodcastEpisodeForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()])
    cover_image = FileField("Cover Image", validators=[FileAllowed(["jpg", "jpeg", "png", "webp"])])
    audio_file = FileField("Audio File", validators=[FileAllowed(["mp3", "m4a", "ogg", "wav", "webm"])])
    duration = IntegerField("Duration (seconds)", validators=[Optional(), NumberRange(min=0)])
    episode_number = IntegerField("Episode Number", validators=[Optional(), NumberRange(min=1)])
    published_at = DateTimeLocalField("Publish At", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Save")
