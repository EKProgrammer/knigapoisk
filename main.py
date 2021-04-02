from flask import Flask, render_template, redirect, request
from random import choice
# поговорки
from sayings import SAYINGS
from data.search_form import SearchForm
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


@app.route('/', methods=['GET', 'POST'])
def index():
    # Главная страница
    form = SearchForm()
    if request.method == 'POST' and form.validate_on_submit():
        return redirect(f"/search/{form.title.data}")
    return render_template('index.html', form=form, saying=choice(SAYINGS))


@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q):
    # q - книга, langRestrict - язык
    response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={q}&langRestrict=ru").json()
    # print(response)
    # Собираю данные из запроса и формурую таблицу с 3 столбцами
    # В ячейке - миниатюра, название книги и автор
    books = []
    # Если количество найденных книг будет рано 0,
    # то books будет пустой, в шаблоне на основе этого делается анализ
    if response['totalItems']:
        for row_index in range(len(response['items']) // 3 + 1):
            row = []
            if (row_index + 1) * 3 <= len(response['items']):
                slice = response['items'][row_index * 3:(row_index + 1) * 3]
            else:
                # делаем срез оставшиеся 2 книгу или 1 книгу
                slice = response['items'][row_index * 3:]
            for book in slice:
                info = book['volumeInfo']
                # Проверка на существование автора
                if 'authors' in info:
                    # Авторов может быть несколько
                    authors = ', '.join(info['authors'])
                else:
                    authors = 'Автор не известен'
                row.append([info['title'],
                            authors,
                            info['imageLinks']['thumbnail']])
            books.append(row)

    form = SearchForm()
    if request.method == 'POST' and form.validate_on_submit():
        return redirect(f"/search/{form.title.data}")
    return render_template('search.html', form=form, saying=choice(SAYINGS), books=books)


def main():
    app.run()


if __name__ == '__main__':
    main()
