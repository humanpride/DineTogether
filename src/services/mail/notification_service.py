from typing import Any

from services.mail.sender import MailSender
from services.mail.template_renderer import render_template


class NotificationService:
    """Сервис уведомлений."""

    def __init__(self) -> None:
        """Инициализировать сервис уведомлений."""
        self.mail_sender = MailSender()

    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template_name: str,
        **context: Any,
    ) -> None:
        """Отправить уведомление по указанному шаблону."""
        body = render_template(
            template_name,
            **context,
        )

        await self.mail_sender.send(
            recipient=recipient,
            subject=subject,
            body=body,
        )


notification_service = NotificationService()
