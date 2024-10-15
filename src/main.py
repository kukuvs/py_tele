"""Empty module."""

import io
import json
import logging
import os
import re
import time

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import CommandStart
from aiogram.types import ContentType, File, Message
from aiogram.utils import executor

from config import load_config
from Filepars import Parser
from MIstral import MistralClient


# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Загрузка конфигурации и инициализация клиентов
config = load_config('./1.txt')
TOKEN = config.telegram_token
mistral_client = MistralClient(api_key=config.mistral_api_key)


# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


# Путь к JSON-файлу с белым списком пользователей
WHITELIST_FILE = './w.json'


def load_whitelist():
    """Загружает белый список пользователей из JSON-файла"""
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r', encoding="utf-8") as file:
            data = json.load(file)
            return data.get("whitelist", [])
    return []


def save_whitelist(whitelist):
    """Сохраняет белый список пользователей в JSON-файл"""
    with open(WHITELIST_FILE, 'w', encoding="utf-8") as file:
        json.dump({"whitelist": whitelist}, file, indent=4)


def is_user_allowed(user_id):
    """Проверяет, находится ли пользователь в белом списке"""
    whitelist = load_whitelist()
    return str(user_id) in whitelist


@dp.message_handler(CommandStart())
async def command_start_handler(message: Message):
    """Обрабатывает команду /start"""
    if is_user_allowed(message.from_user.id):
        await message.reply("Здарова сталкер!")
    else:
        await message.reply("или давай денег или иди нахер.")


@dp.message_handler(content_types=ContentType.TEXT)
async def handle_text_message(message: Message):
    """Handles text messages"""
    if not is_user_allowed(message.from_user.id):
        logging.error(f"{time.strftime('%H:%M:%S')} Message from %s (%s): %s", message.from_user.id, message.from_user.first_name, message.text)
        await message.reply("или давай денег или иди нахер.")
        return

    text = message.text
    urls = re.findall(r'https?://[^\s]+', text)

    logging.info(f"{time.strftime('%H:%M:%S')} Message from %s (%s): %s", message.from_user.id, message.from_user.first_name, message.text)

    if urls:
        url = urls[0]
        parser = Parser(b'', 'html')

        try:
            html_text = await parser.read_from_html(url)
            request_text = f"{text.replace(url, '').strip()}\n\n{html_text}"
            response = await mistral_client.generate_text_async(request_text)
            await split_and_send_message(message, response)
        except (OSError, IOError, ValueError) as e:
            logger.error("Error while processing HTML: %s", e)
            await message.reply("Произошла ошибка при извлечении текста с веб-страницы.")
    else:
        response = await mistral_client.generate_text_async(text)
        await split_and_send_message(message, response)


async def split_and_send_message(message: Message, response: str):
    """Splits the response into chunks of 4000 characters and sends them"""
    for i in range(0, len(response), 4000):
        await message.reply(response[i:i + 4000])


@dp.message_handler(content_types=ContentType.DOCUMENT)
async def handle_document(message: Message):
    """Скачивание файла, его обработка и отправка в Mistral"""
    if not is_user_allowed(message.from_user.id):
        await message.reply("или давай денег или иди нахер.")
        return

    document = message.document
    logging.info(f"{time.strftime('%H:%M:%S')} Message from %s (%s): %s", message.from_user.id, message.from_user.first_name, message.text)

    file_id = document.file_id
    file: File = await bot.get_file(file_id)

    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    buffer.seek(0)

    ext = os.path.splitext(document.file_name)[1].lower()
    parser = Parser(buffer.getvalue(), ext)

    try:
        if ext == '.txt':
            text = parser.read_from_txt()
        elif ext == '.pdf':
            text = parser.read_from_pdf()
        elif ext == '.docx':
            text = parser.read_from_docx()
        else:
            text = "Неподдерживаемый формат файла."
            await message.reply(text)
            return

        user_question = message.caption if message.caption else message.text
        request_text = f"{user_question}\n\n{text}"

        response = await mistral_client.generate_text_async(request_text)

        await split_and_send_message(message, response)

    except (OSError, IOError, ValueError) as e:
        logger.error("Error while reading file: %s", e)
        await message.reply("An error occurred while processing the file.")


async def on_shutdown(dp_: any):
    """Закрывает все открытые сессии при завершении работы бота"""
    await dp_.storage.close()
    await dp_.storage.wait_closed()
    await bot.session.close()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
