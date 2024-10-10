class Config:
    def __init__(self, telegram_token: str, mistral_api_key: str):
        self.telegram_token = telegram_token
        self.mistral_api_key = mistral_api_key

def load_config(file_path: str) -> Config:
    """Загружает конфигурацию из текстового файла."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file.readlines()]

    if len(lines) < 2:
        raise ValueError("Invalid config file format")

    # Возвращаем объект конфигурации с токенами
    return Config(
        telegram_token=lines[0],
        mistral_api_key=lines[1]
    )
