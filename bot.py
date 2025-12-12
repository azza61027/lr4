import logging
import requests
import urllib.parse
import random
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8271690016:AAHsLPpmNgWoScimkpaYe7a718cwUFRIFrM"
OPEN_LIBRARY_API = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

AUTHOR_TRANSLATIONS = {
    'толстой': 'Leo Tolstoy',
    'достоевский': 'Fyodor Dostoevsky',
    'пушкин': 'Alexander Pushkin',
    'гоголь': 'Nikolai Gogol',
    'чехов': 'Anton Chekhov',
    'булгаков': 'Mikhail Bulgakov',
    'набоков': 'Vladimir Nabokov',
    'орвелл': 'George Orwell',
    'кинг': 'Stephen King',
    'роулинг': 'J.K. Rowling',
    'хемингуэй': 'Ernest Hemingway',
}

TITLE_TRANSLATIONS = {
    'война и мир': 'War and Peace',
    'преступление и наказание': 'Crime and Punishment',
    'анна каренина': 'Anna Karenina',
    'мастер и маргарита': 'The Master and Margarita',
    'идиот': 'The Idiot',
    'братья карамазовы': 'The Brothers Karamazov',
    '1984': '1984',
    'гарри поттер': 'Harry Potter',
}


def translate_author(query: str) -> str:
    query_lower = query.lower()

    if query_lower in AUTHOR_TRANSLATIONS:
        return AUTHOR_TRANSLATIONS[query_lower]

    for ru, en in AUTHOR_TRANSLATIONS.items():
        if ru in query_lower:
            return en

    return query


def translate_title(query: str) -> str:
    query_lower = query.lower()

    if query_lower in TITLE_TRANSLATIONS:
        return TITLE_TRANSLATIONS[query_lower]

    for ru, en in TITLE_TRANSLATIONS.items():
        if ru in query_lower:
            return en

    return query


def search_books_by_title(title: str):
    translated_title = translate_title(title)

    search_params = [
        {'q': translated_title, 'limit': 5},
        {'title': translated_title, 'limit': 5},
    ]

    for params in search_params:
        try:
            response = requests.get(OPEN_LIBRARY_API, params=params, timeout=10)
            logger.info(f"Поиск книги: '{title}' -> '{translated_title}'")

            if response.status_code == 200:
                data = response.json()
                books = data.get('docs', [])
                if books:
                    logger.info(f"Найдено книг: {len(books)}")
                    return books
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            continue

    return []


def search_books_by_author_google(author: str):
    """Поиск книг по автору через Google Books API"""
    translated_author = translate_author(author)

    try:
        params = {'q': f'inauthor:{translated_author}', 'maxResults': 5}
        response = requests.get(GOOGLE_BOOKS_API, params=params, timeout=10)
        logger.info(f"Поиск автора в Google Books: '{author}' -> '{translated_author}'")

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            books = []
            for item in items[:5]:
                volume_info = item.get('volumeInfo', {})
                book_data = {
                    'title': volume_info.get('title', 'Без названия'),
                    'author_name': volume_info.get('authors', ['Неизвестно']),
                    'published_date': volume_info.get('publishedDate', 'Неизвестно'),
                    'description': volume_info.get('description', 'Нет описания'),
                    'industry_identifiers': volume_info.get('industryIdentifiers', []),
                    'average_rating': volume_info.get('averageRating'),
                    'ratings_count': volume_info.get('ratingsCount')
                }
                books.append(book_data)

            logger.info(f"Найдено книг в Google Books: {len(books)}")
            return books

    except Exception as e:
        logger.error(f"Ошибка поиска автора в Google Books: {e}")

    return []


def search_books_by_author_openlibrary(author: str):
    """Пробуем Open Library как fallback"""
    translated_author = translate_author(author)

    try:
        params = {'author': translated_author, 'limit': 5}
        response = requests.get(OPEN_LIBRARY_API, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            books = data.get('docs', [])
            if books:
                return books
    except:
        pass

    return []


def get_book_rating(isbn: str):
    if not isbn:
        return {'rating': None, 'count': None}

    try:
        response = requests.get(GOOGLE_BOOKS_API, params={'q': f'isbn:{isbn}'}, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('totalItems', 0) > 0:
                book_info = data['items'][0]['volumeInfo']
                return {
                    'rating': book_info.get('averageRating'),
                    'count': book_info.get('ratingsCount')
                }
        return {'rating': None, 'count': None}
    except Exception as e:
        logger.error(f"Ошибка рейтинга: {e}")
        return {'rating': None, 'count': None}


def get_isbn_from_book(book):
    """Извлекаем ISBN из данных книги"""
    if 'industry_identifiers' in book:
        for identifier in book.get('industry_identifiers', []):
            if identifier.get('type') in ['ISBN_13', 'ISBN_10']:
                return identifier.get('identifier')

    if 'isbn' in book:
        isbn_list = book.get('isbn', [])
        if isbn_list:
            return isbn_list[0]

    return None


def start(update: Update, context: CallbackContext):
    try:
        welcome_text = (
            "Книжный бот\n\n"
            "Команды:\n"
            "/find <название> - поиск книги по названию\n"
            "/author <автор> - поиск книг по автору\n"
            "/random - случайная книга\n"
            "/help - помощь\n\n"
            "Примеры:\n"
            "/find Harry Potter\n"
            "/find 1984\n"
            "/author Stephen King\n"
            "/author Leo Tolstoy\n"
            "/author Толстой\n"
            "/random"
        )
        update.message.reply_text(welcome_text)
    except Exception as e:
        logger.error(f"Ошибка /start: {e}")
        update.message.reply_text("Ошибка!")


def find_book(update: Update, context: CallbackContext):
    try:
        if not context.args:
            update.message.reply_text(
                "Укажите название. Примеры:\n"
                "/find Harry Potter\n"
                "/find 1984\n"
                "/find War and Peace"
            )
            return

        title = ' '.join(context.args)
        update.message.reply_text(f"Ищу книгу: {title}...")

        books = search_books_by_title(title)

        if not books:
            update.message.reply_text(
                f"Книги по запросу '{title}' не найдены.\n"
                "Попробуйте английское название или другой запрос."
            )
            return

        response = f"Найдено книг: {len(books)}\n\n"

        for i, book in enumerate(books[:3], 1):
            book_title = book.get('title', 'Без названия')
            authors = book.get('author_name', [])
            author = authors[0] if authors else 'Неизвестно'
            year = book.get('first_publish_year', book.get('published_date', 'Неизвестно'))

            isbn = get_isbn_from_book(book)
            rating = get_book_rating(isbn)

            response += f"{i}. {book_title}\n"
            response += f"   Автор: {author}\n"
            response += f"   Год: {year}\n"

            if rating and rating['rating']:
                stars = '★' * int(float(rating['rating']))
                response += f"   Рейтинг: {rating['rating']}/5 {stars}\n"

            response += "\n"

        update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Ошибка /find: {e}")
        update.message.reply_text("Ошибка при поиске.")


def find_by_author(update: Update, context: CallbackContext):
    try:
        if not context.args:
            update.message.reply_text(
                "Укажите автора. Примеры:\n"
                "/author Stephen King\n"
                "/author Leo Tolstoy\n"
                "/author George Orwell\n"
                "/author Толстой\n"
                "/author Достоевский"
            )
            return

        author = ' '.join(context.args)
        update.message.reply_text(f"Ищу книги автора: {author}...")

        books = search_books_by_author_google(author)

        if not books:
            books = search_books_by_author_openlibrary(author)

        if not books:
            update.message.reply_text(
                f"Книги автора '{author}' не найдены.\n\n"
                "Попробуйте:\n"
                "Английское имя (Leo Tolstoy)\n"
                "Фамилию (Tolstoy)\n"
                "Другого автора\n\n"
                "Популярные авторы:\n"
                "Stephen King\n"
                "J.K. Rowling\n"
                "George Orwell\n"
                "Leo Tolstoy\n"
                "Fyodor Dostoevsky"
            )
            return

        response = f"Книги автора {author}:\n\n"

        for i, book in enumerate(books[:3], 1):
            book_title = book.get('title', 'Без названия')
            authors = book.get('author_name', [])
            book_author = authors[0] if authors else author
            year = book.get('published_date', book.get('first_publish_year', 'Неизвестно'))

            if year and len(year) > 4:
                year = year[:4]

            isbn = get_isbn_from_book(book)
            rating = book.get('average_rating')
            rating_count = book.get('ratings_count')

            response += f"{i}. {book_title}\n"
            response += f"   Автор: {book_author}\n"

            if year and year != 'Неизвестно':
                response += f"   Год: {year}\n"

            if rating:
                stars = '★' * int(float(rating))
                response += f"   Рейтинг: {rating}/5 {stars}\n"
                if rating_count:
                    response += f"   Оценок: {rating_count}\n"

            response += "\n"

        update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Ошибка /author: {e}")
        update.message.reply_text("Ошибка при поиске.")


def random_book(update: Update, context: CallbackContext):
    try:
        update.message.reply_text("Выбираю случайную книгу...")

        popular_authors = [
            'Stephen King', 'J.K. Rowling', 'George Orwell',
            'Leo Tolstoy', 'Fyodor Dostoevsky', 'Ernest Hemingway',
            'Jane Austen', 'Mark Twain', 'Charles Dickens'
        ]

        author = random.choice(popular_authors)
        books = search_books_by_author_google(author)

        if not books:
            books = search_books_by_title(random.choice(['Harry Potter', '1984', 'The Hobbit']))

        if books:
            book = random.choice(books[:3])
            book_title = book.get('title', 'Без названия')
            authors = book.get('author_name', [])
            author_name = authors[0] if authors else 'Неизвестно'
            year = book.get('published_date', book.get('first_publish_year', 'Неизвестно'))

            if year and len(year) > 4:
                year = year[:4]

            isbn = get_isbn_from_book(book)
            rating = book.get('average_rating')

            if not rating and isbn:
                rating_info = get_book_rating(isbn)
                rating = rating_info['rating']

            response = "Случайная книга:\n\n"
            response += f"Название: {book_title}\n"
            response += f"Автор: {author_name}\n"

            if year and year != 'Неизвестно':
                response += f"Год: {year}\n"

            if rating:
                stars = '★' * int(float(rating))
                response += f"Рейтинг: {rating}/5 {stars}\n"

            response += "\nКоманды:\n"
            response += "/random - другая книга\n"
            response += "/author <автор> - поиск по автору\n"
            response += "/find <название> - поиск по названию"

            update.message.reply_text(response)
        else:
            update.message.reply_text(
                "Не удалось найти книгу. Попробуйте:\n"
                "/find Harry Potter\n"
                "/author Stephen King\n"
                "/find 1984"
            )

    except Exception as e:
        logger.error(f"Ошибка /random: {e}")
        update.message.reply_text("Ошибка.")


def help_command(update: Update, context: CallbackContext):
    try:
        help_text = (
            "Помощь\n\n"
            "Доступные команды:\n"
            "/find <название> - поиск книги\n"
            "/author <автор> - поиск по автору\n"
            "/random - случайная книга\n"
            "/start - начать заново\n\n"
            "Примеры:\n"
            "/find Harry Potter\n"
            "/find 1984\n"
            "/author Stephen King\n"
            "/author Leo Tolstoy\n"
            "/author Толстой\n"
            "/author Достоевский\n"
            "/random\n\n"
            "Поиск по автору работает на русском и английском."
        )
        update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Ошибка /help: {e}")
        update.message.reply_text("Ошибка.")


def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        update.message.reply_text("Произошла ошибка. Попробуйте позже.")


def main():
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("find", find_book))
        dp.add_handler(CommandHandler("author", find_by_author))
        dp.add_handler(CommandHandler("random", random_book))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_error_handler(error_handler)

        print("=" * 50)
        print("Бот запущен!")
        print("Поиск по автору теперь работает через Google Books API")
        print("Тестируйте:")
        print("/author Толстой")
        print("/author Stephen King")
        print("/find Harry Potter")
        print("=" * 50)

        updater.start_polling()
        updater.idle()

    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")


if __name__ == '__main__':
    main()