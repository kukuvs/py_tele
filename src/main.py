from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, File, ContentType
from aiogram.dispatcher.filters import CommandStart
from aiogram.utils import executor
from config import load_config
from MIstral import MistralClient
from Filepars import Parser  

import logging
import io
import re
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка конфигурации и инициализация клиентов
config = load_config('src/1.txt')
TOKEN = config.telegram_token
mistral_client = MistralClient(api_key=config.mistral_api_key)

# Создаем бота и диспетчер
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(CommandStart())
async def command_start_handler(message: Message):
    """Обрабатывает команду /start"""
    await message.reply("Здарова сталкер!")

@dp.message_handler(content_types=ContentType.TEXT)
async def message_handler(message: Message):
    """Обрабатывает текстовые сообщения"""
    # Находим URL в сообщении
    urls = re.findall(r'https?://[^\s]+', message.text)
    
    # Если найдены ссылки
    if urls:
        # Предполагается, что первая найденная ссылка будет использоваться
        url = urls[0]
        parser = Parser(b'', 'html')  # Пустой байт-контент, тип 'html'
        
        try:
            # Извлекаем текст из HTML
            html_text = await parser.read_from_html(url)  # Используем асинхронный метод
            
            # Убираем ссылку из текста сообщения
            cleaned_text = message.text.replace(url, '').strip()
            
            # Объединяем текст HTML с оставшимся текстом сообщения
            request_text = f"{cleaned_text}\n\n{html_text}"

            # Отправляем запрос в Mistral
            response =  await mistral_client.generate_text_async(request_text)
            await message.reply(response)  # Отправляем ответ пользователю
            
        except Exception as e:
            logger.error(f"Ошибка при обработке HTML: {e}")
            await message.reply("Произошла ошибка при извлечении текста с веб-страницы.")
    else:
        response = await mistral_client.generate_text_async(message.text)
        await message.reply(response)


@dp.message_handler(content_types=ContentType.DOCUMENT)
async def handle_document(message: Message):
    """Скачивание файла, его обработка и отправка в Mistral"""
    document = message.document

    # Получаем file_id и загружаем файл
    file_id = document.file_id
    file: File = await message.bot.get_file(file_id)

    # Загружаем файл во временный буфер
    buffer = io.BytesIO()
    await message.bot.download_file(file.file_path, buffer)
    buffer.seek(0)  # Перемещаем указатель в начало буфера

    # Определяем расширение файла
    ext = os.path.splitext(document.file_name)[1].lower()

    # Создаём экземпляр Parser, передавая содержимое и расширение
    parser = Parser(buffer.getvalue(), ext)

    # Чтение содержимого файла
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
        
        # Объединяем текст файла с текстом вопроса пользователя
        user_question = message.caption if message.caption else message.text
        request_text = f"{user_question}\n\n{text}"

        # Отправляем запрос в Mistral
        response = await mistral_client.generate_text_async(request_text)

        # Проверка длины ответа и разбиение на части
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await message.reply(response[i:i + 4000])
        else:
            await message.reply(response)  # Отправляем ответ пользователю
            
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        await message.reply("Произошла ошибка при обработке файла.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
