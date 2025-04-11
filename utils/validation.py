# utils/validation.py

import re

class ValidationError(Exception):
    """Исключение для ошибок валидации."""
    pass

def validate_positive_number(value: float, name: str):
    """
    Проверяет, что значение является положительным числом.
    :param value: Значение для проверки.
    :param name: Название параметра для вывода в ошибке.
    :raises ValidationError: Если значение не является положительным числом.
    """
    if value <= 0:
        raise ValidationError(f"{name} должно быть положительным числом.")

def validate_api_key(api_key: str):
    """
    Проверяет формат API-ключа.
    :param api_key: API-ключ для проверки.
    :raises ValidationError: Если ключ имеет недопустимый формат.
    """
    if not re.match(r"^[A-Za-z0-9]+$", api_key):
        raise ValidationError("API-ключ содержит недопустимые символы. Разрешены только буквы и цифры.")

def validate_api_secret(api_secret: str):
    """
    Проверяет формат API-секрета.
    :param api_secret: API-секрет для проверки.
    :raises ValidationError: Если секрет имеет недопустимый формат.
    """
    if not re.match(r"^[A-Za-z0-9/+=]+$", api_secret):
        raise ValidationError("API-секрет содержит недопустимые символы. Разрешены буквы, цифры, '/', '+' и '='.")

def validate_period(period: int):
    """
    Проверяет, что период является положительным целым числом.
    :param period: Период в днях.
    :raises ValidationError: Если период недопустимый.
    """
    if not isinstance(period, int) or period <= 0:
        raise ValidationError("Период должен быть положительным целым числом.")