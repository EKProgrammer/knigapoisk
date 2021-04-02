from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class SearchForm(FlaskForm):
    # Форма поиска
    title = StringField(validators=[DataRequired()])
    submit = SubmitField('Найти')
