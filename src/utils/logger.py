"""Модуль логгирования."""

import logging
from pathlib import Path


def setup_logger(
    name: str = "calmak",
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """Настраивает и возвращает логгер.

    Args:
        name: Имя логгера
        level: Уровень логгирования
        log_file: Путь к файлу лога (опционально)

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Формат сообщений
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
