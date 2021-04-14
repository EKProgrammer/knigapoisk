from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField, StringField, IntegerField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired


class EditForm(FlaskForm):
    surname = StringField('Фамилия', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('Почта', validators=[DataRequired()])
    age = IntegerField('Возраст', validators=[DataRequired()])
    about = StringField('О себе')
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Зарегистрироваться')