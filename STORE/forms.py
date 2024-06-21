from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from .models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')]
    )
    is_admin = BooleanField('Admin')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class UpdateProductForm(FlaskForm):
    pre = StringField('Prefix', validators=[DataRequired()])
    item = StringField('Item', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    type_material = StringField('Type Material')
    size = StringField('Size')
    color = StringField('Color')
    description = TextAreaField('Description')
    buying_price = FloatField('Buying Price', validators=[DataRequired()])
    selling_price = FloatField('Selling Price', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
