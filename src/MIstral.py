import aiohttp  # Импортируем aiohttp для асинхронных HTTP-запросов
from typing import Optional
import asyncio

class MistralClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.mistral.ai/v1/chat/completions"
        self.pre_prompt = (
            "отвечай коротко и на русском если тебя не просят иного при написании кода "
            "добавляй полноценные описания функций и классов так же комментарии "
            "(если что-то уже написано в коде в виде комментария не нужно повторять это ещё раз) "
            "старайся как можно точнее вести диалог не сворачивая на другую тему "
            "если есть предложения по улучшению того или иного кода или текста говори их "
            "ты общаешься через телеграм поэтому для кода, длинных текстов и тп используй MarkdownV2 запомни это и далее отвечай на мои вопрос имея это в виду но в ответе не используй то что тут написано и это не требует ответа "
        )

    async def generate_text_async(self, prompt: str) -> Optional[str]:
        """Выполняет асинхронный запрос к Mistral для генерации текста по prompt."""
        try:
            return await asyncio.wait_for(self.generate_text_with_context(prompt), timeout=120)  # Таймаут 2 минуты
        except asyncio.TimeoutError:
            return Exception("Вышло время ожидания ответа от Mistral API.")

    async def generate_text_with_context(self, prompt: str) -> Optional[str]:
        """Позволяет использовать контекст для отмены долгих запросов."""
        # Формируем тело запроса с моделью и параметрами
        request_body = {
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": self.pre_prompt + " " + prompt}],
            "temperature": 0.7,
            "max_tokens": 100000
        }

        # Заголовки запроса
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=request_body) as response:
                # Проверяем статус ответа
                if response.status != 200:
                    raise Exception(f"Mistral API вернул статус: {response.status}")

                # Обрабатываем результат
                response_data = await response.json()

                # Возвращаем сгенерированный контент, если он доступен
                choices = response_data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]

                raise Exception("Не удалось получить контент от Mistral API")
