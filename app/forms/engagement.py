from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class CommentForm(FlaskForm):
    display_name = StringField("Name", validators=[Optional(), Length(max=80)])
    body = TextAreaField("Comment", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Post Comment")

class ReportForm(FlaskForm):
    reason = TextAreaField("Reason", validators=[DataRequired(), Length(min=3, max=2000)])
    submit = SubmitField("Report")
