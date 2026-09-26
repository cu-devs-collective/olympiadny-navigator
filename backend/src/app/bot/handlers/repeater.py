import typing

import maxapi
from maxapi.types import (
    Attachment,
    AttachmentUpload,
    InputMedia,
    InputMediaBuffer,
    MessageCreated,
)


async def repeat_message(event: MessageCreated) -> None:
    """Send an incoming message's text and attachments back to its chat."""

    body = event.message.body
    if body is None or (not body.text and not body.attachments):
        return

    attachments = typing.cast(
        "list[Attachment | InputMedia | InputMediaBuffer | AttachmentUpload] | None",
        body.attachments,
    )
    await event.message.answer(text=body.text, attachments=attachments)


def create_repeater_router() -> maxapi.Router:
    router = maxapi.Router(router_id="repeater")
    router.message_created.register(repeat_message)
    return router
