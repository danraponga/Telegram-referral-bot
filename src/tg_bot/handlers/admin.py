import csv
from io import StringIO, BytesIO
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
    BufferedInputFile,
)
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from aiogram_i18n import I18nContext
from asyncpg import UniqueViolationError

from tg_bot import config
from tg_bot.models.role import UserRole
from tg_bot.states.states import AdminPanel

router = Router()


@router.message(Command(commands="admin"))
async def open_admin_panel(
    message: Message, dialog_manager: DialogManager, role: UserRole
):
    if role == UserRole.ADMIN:
        await dialog_manager.start(AdminPanel.menu, mode=StartMode.RESET_STACK)


async def add_channel(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    i18n = dialog_manager.middleware_data["i18n_context"]
    pattern = r"^https://t\.me/(?P<username>[a-zA-Z0-9_]{5,32})$"
    match = re.match(pattern, message.text)
    if not match:
        await message.answer(i18n.admin.wrong_link_format())
    else:
        channel = "@" + match.group("username")
        member = await message.bot.get_chat_member(channel, config.BOT_ID)
        if member.status != "administrator":
            await message.answer(i18n.admin.bot_not_admin())
        else:
            checkbox = dialog_manager.find("check_required_channel")
            required = checkbox.is_checked()
            try:
                await dialog_manager.middleware_data["repo"].add_channel(
                    message.text, required
                )
                await message.answer(i18n.admin.channel_added())
            except UniqueViolationError:
                await message.answer(i18n.admin.channel_already_added())
    await dialog_manager.switch_to(AdminPanel.menu)


async def remove_channel(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    i18n = dialog_manager.middleware_data["i18n_context"]
    try:
        await dialog_manager.middleware_data["repo"].delete_channel(
            message.text
        )
        await message.answer(i18n.admin.channel_removed())
    except ValueError:
        await message.answer(i18n.admin.channel_already_removed())

    await dialog_manager.switch_to(AdminPanel.menu)


async def decide_newsletter(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    i18n = dialog_manager.middleware_data["i18n_context"]
    if button.widget_id == "confirm_newsletter":
        users = await dialog_manager.middleware_data["repo"].fetch_users_id()
        newsletter_message = dialog_manager.dialog_data["newsletter_message"]
        for user in users:
            await callback.bot.send_message(user, newsletter_message)

        await callback.message.answer(i18n.admin.newsletter_sent())

    await dialog_manager.switch_to(AdminPanel.menu)


async def dump_table(
    query: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    users = await dialog_manager.middleware_data["repo"].fetch_users_data()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Телеграм айди",
            "Имя пользователя",
            "Поинты",
            "Количество рефералов",
            "Кошелёк",
        ]
    )
    for user in users:
        writer.writerow(
            [
                user["telegram_id"],
                user["username"],
                user["points"],
                user["referrals_count"],
                user["wallet"],
            ]
        )
    output.seek(0)
    bytes_output = BytesIO(output.read().encode("utf-8"))

    document = BufferedInputFile(bytes_output.read(), "users.csv")
    await query.message.answer_document(document=document)
    await dialog_manager.switch_to(AdminPanel.menu)
