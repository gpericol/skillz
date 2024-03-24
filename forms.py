from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, StringField, PasswordField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, EqualTo
from models import User
from wtforms.validators import Email
from wtforms.validators import NumberRange
from wtforms.fields import DecimalField

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateUserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    surname = StringField('Surname', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')])

class PrivacyForm(FlaskForm):
    accepted_privacy = SelectField('Accepted Privacy', choices=[('True', 'Yes'), ('False', 'No')])

class CreateCategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    parent_id = SelectField('Parent Category', coerce=int, choices=[(0, 'No Parent')])
    submit = SubmitField('Create Category')

class DeleteCategoryForm(FlaskForm):
    category_id = HiddenField('Category ID', validators=[DataRequired()])

class CreateSkillForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Create Skill')


class DeleteSkillForm(FlaskForm):
    skill_id = HiddenField('Skill ID', validators=[DataRequired()])
        
class UpdateSkillForm(FlaskForm):
    skill_id = HiddenField('Skill ID', validators=[DataRequired()])
    level = SelectField('Level', coerce=int, choices=[(0,'0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])