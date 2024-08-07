import csv
from io import StringIO, BytesIO
import re
from venv import logger

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
from tg_bot.services.repository import Repo
from tg_bot.states.states import Admin

from aiogram.exceptions import TelegramForbiddenError

router = Router()


@router.message(Command(commands="admin"))
async def open_admin_panel(
    message: Message, dialog_manager: DialogManager, role: UserRole
):
    if role == UserRole.ADMIN:
        await dialog_manager.start(Admin.menu, mode=StartMode.RESET_STACK)
    else:
        await dialog_manager.show()


async def add_channel(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    i18n = dialog_manager.middleware_data["i18n_context"]
    checkbox = dialog_manager.find("check_required_channel")
    required = checkbox.is_checked()
    try:
        await dialog_manager.middleware_data["repo"].add_channel(
            message.text, required
        )
        await message.answer(i18n.admin.channel_added())
    except UniqueViolationError:
        await message.answer(i18n.admin.channel_already_added())
    await dialog_manager.switch_to(Admin.menu)


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

    await dialog_manager.switch_to(Admin.menu)


async def send_newsletter(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
):
    i18n = dialog_manager.middleware_data["i18n_context"]
    users = await dialog_manager.middleware_data["repo"].fetch_users_id()

    for user in users:
        try:
            await message.copy_to(int(user))
        except TelegramForbiddenError:
            pass

    await message.answer(i18n.admin.newsletter_sent())
    await dialog_manager.switch_to(Admin.menu)


async def add_user_points(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    i18n: I18nContext = dialog_manager.middleware_data["i18n_context"]
    repo: Repo = dialog_manager.middleware_data["repo"]
    try:
        user_id, points = map(int, message.text.split("="))
        if not await repo.get_by_telegram_id(user_id):
            await message.answer(i18n.admin.points_error())
            return
        await repo.update_points(user_id, points)
        await message.answer(i18n.admin.points_added())
        await dialog_manager.switch_to(Admin.menu)
    except Exception as e:
        logger.error(f"add_user_points error: {e}")
        await message.answer(i18n.admin.points_error())


async def remove_user_points(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    i18n: I18nContext = dialog_manager.middleware_data["i18n_context"]
    repo: Repo = dialog_manager.middleware_data["repo"]
    try:
        user_id, points = map(int, message.text.split("="))
        if not await repo.get_by_telegram_id(user_id):
            await message.answer(i18n.admin.points_error())
            return
        await repo.remove_points(user_id, points)
        await message.answer(i18n.admin.points_removed())
        await dialog_manager.switch_to(Admin.menu)
    except Exception as e:
        logger.error(f"remove_user_points error: {e}")
        await message.answer(i18n.admin.points_error())


async def dump_table(
    message: Message, widget: MessageInput, dialog_manager: DialogManager
):
    try:
        users = await dialog_manager.middleware_data["repo"].fetch_top_referrers_for_last_n_days(int(message.text))
    except Exception as e:
        logger.info(e)
        if message.text == "all":
            users = await dialog_manager.middleware_data["repo"].fetch_users_data()
        else:
            await message.answer('Неверный формат, разрешены только числа или "все"')
            return

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Телеграм айди",
            "Имя пользователя",
            "Количество рефералов",
            "Поинты"
            "Кошелёк",
        ]
    )
    for user in users:
        writer.writerow(
            [
                user["telegram_id"],
                user["username"],
                user["referrals_count"],
                user["points"],
                user["wallet"],
            ]
        )
    output.seek(0)
    bytes_output = BytesIO(output.read().encode("utf-8"))

    document = BufferedInputFile(bytes_output.read(), "users.csv")
    await message.answer_document(document=document)
    await dialog_manager.switch_to(Admin.menu)
