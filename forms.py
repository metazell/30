from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

class MessageForm(FlaskForm):
    """Form for adding/editing messages."""
    text = TextAreaField('Text', validators=[DataRequired()])

class UserAddForm(FlaskForm):
    """Form for adding users."""
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    image_url = StringField('Image URL (Optional)', validators=[Optional()])

class UserEditForm(FlaskForm):
    """Form for editing users."""
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    image_url = StringField('Image URL (Optional)', validators=[Optional()])
    header_image_url = StringField('Header Image URL (Optional)', validators=[Optional()])
    bio = TextAreaField('Tell us about yourself (Optional)', validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])

class LoginForm(FlaskForm):
    """Login form."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    