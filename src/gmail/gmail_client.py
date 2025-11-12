"""
Модуль работы с Gmail API
Аутентификация, чтение писем, пометка как прочитанные
"""

import os
import pickle
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import sys

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GMAIL_CREDENTIALS

# Scopes для Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def authenticate():
    """
    Аутентификация через Gmail API с использованием OAuth2

    Returns:
        Gmail API service объект

    Raises:
        Exception если аутентификация не удалась
    """
    creds = None
    token_path = 'credentials/token.pickle'

    # 1. Попытка загрузить сохраненный токен
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 2. Проверить валидность токена
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Обновить истекший токен
            creds.refresh(Request())
        else:
            # Запустить OAuth2 flow для получения нового токена
            if not os.path.exists(GMAIL_CREDENTIALS):
                raise Exception(f"Файл credentials не найден: {GMAIL_CREDENTIALS}")

            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Сохранить токен для будущих запусков
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # 3. Создать Gmail API service
    service = build('gmail', 'v1', credentials=creds)

    return service


def fetch_unread_emails(service, query: str = 'is:unread') -> List[Dict]:
    """
    Получает список непрочитанных писем по запросу

    Args:
        service: Gmail API service объект
        query: Поисковый запрос (по умолчанию 'is:unread')

    Returns:
        Список словарей с метаданными писем: id, subject, from, date
    """
    try:
        # 1. Выполнить поиск писем
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return []

        # 2. Получить метаданные для каждого письма
        email_list = []
        for msg in messages:
            msg_id = msg['id']

            # Получить полные данные письма
            message = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()

            # Извлечь заголовки
            headers = message.get('payload', {}).get('headers', [])
            subject = ''
            from_email = ''
            date = ''

            for header in headers:
                name = header.get('name', '')
                value = header.get('value', '')

                if name == 'Subject':
                    subject = value
                elif name == 'From':
                    from_email = value
                elif name == 'Date':
                    date = value

            email_list.append({
                'id': msg_id,
                'subject': subject,
                'from': from_email,
                'date': date
            })

        return email_list

    except Exception as e:
        print(f"Ошибка получения писем: {e}")
        return []


def get_email_body(service, msg_id: str) -> str:
    """
    Получает текст тела письма по ID

    Args:
        service: Gmail API service объект
        msg_id: ID письма

    Returns:
        Текст письма (plain text или HTML)
    """
    try:
        # Получить полное письмо
        message = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        payload = message.get('payload', {})

        # Функция для рекурсивного поиска тела письма
        def get_body_from_parts(parts):
            body = ''
            for part in parts:
                mime_type = part.get('mimeType', '')

                # Если это multipart - рекурсия
                if 'parts' in part:
                    body += get_body_from_parts(part['parts'])
                # Если text/plain
                elif mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                        body += decoded
                # Если text/html (запасной вариант)
                elif mime_type == 'text/html' and not body:
                    data = part.get('body', {}).get('data', '')
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                        body += decoded

            return body

        # Попытка 1: Если есть parts
        if 'parts' in payload:
            body_text = get_body_from_parts(payload['parts'])
        else:
            # Попытка 2: Прямое тело письма
            data = payload.get('body', {}).get('data', '')
            if data:
                body_text = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                body_text = ''

        return body_text

    except Exception as e:
        print(f"Ошибка получения тела письма: {e}")
        return ''


def mark_as_read(service, msg_id: str) -> bool:
    """
    Помечает письмо как прочитанное

    Args:
        service: Gmail API service объект
        msg_id: ID письма

    Returns:
        True если успешно, False если ошибка
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

        return True

    except Exception as e:
        print(f"Ошибка пометки письма как прочитанного: {e}")
        return False
