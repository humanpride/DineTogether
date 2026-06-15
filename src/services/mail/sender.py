from email.message import EmailMessage

import aiosmtplib

from core.settings import settings


class MailSender:
    """Сервис для отправки электронных писем через SMTP."""

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        subtype: str = 'html',
    ) -> None:
        """Отправить электронное письмо.

        Args:
            recipient: Email-адрес получателя.
            subject: Тема письма.
            body: Содержимое письма.
            subtype: Тип содержимого письма.
                Используйте 'html' для HTML-разметки
                или 'plain' для обычного текста.

        """
        message = EmailMessage()

        message['From'] = settings.from_email
        message['To'] = recipient
        message['Subject'] = subject

        message.set_content(body, subtype=subtype)

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
        )
