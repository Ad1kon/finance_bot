"""
Транскрибация голосовых сообщений в текст через Groq Whisper API.
Groq принимает файлы .ogg напрямую — конвертация не требуется.
"""

from groq import Groq
from config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


async def transcribe_voice(file_path: str) -> str:
    """
    file_path — путь к локальному .ogg файлу голосового сообщения.
    Возвращает распознанный текст (может быть на русском/казахском).
    """
    if _client is None:
        raise RuntimeError(
            "GROQ_API_KEY не задан — распознавание голоса недоступно. "
            "Добавьте ключ в .env, чтобы включить эту функцию."
        )

    with open(file_path, "rb") as f:
        transcription = _client.audio.transcriptions.create(
            file=(file_path, f.read()),
            model="whisper-large-v3",
            language=None,  # автоопределение языка (ru/kk/en)
            response_format="text",
        )
    return str(transcription).strip()
