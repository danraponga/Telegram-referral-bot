from typing import Literal


class UserUpdateRepo:
    def __init__(self, db):
        self.db = db

    async def update_check_in(self, tg_id: int) -> None:
        await self.db.execute(
            """
            UPDATE users
            SET last_check_in = NOW()
            WHERE telegram_id = $1
            """,
            tg_id,
        )

    async def update_points(self, tg_id: int, points: int) -> None:
        await self.db.execute(
            """
            UPDATE users
            SET points = points + $1
            WHERE telegram_id = $2
            """,
            points,
            tg_id,
        )

    async def remove_points(self, tg_id: int, points: int) -> None:
        await self.db.execute(
            """
            UPDATE users
            SET points = points - $1
            WHERE telegram_id = $2
            """,
            points,
            tg_id,
        )

    async def set_user_locale(
        self, tg_id: int, locale: Literal["ru", "en"]
    ) -> None:
        await self.db.execute(
            "UPDATE users SET language = $2 WHERE telegram_id = $1",
            tg_id,
            locale,
        )

    async def set_wallet(self, tg_id: int, wallet: str) -> None:
        await self.db.execute(
            "UPDATE users SET wallet = $2 WHERE telegram_id = $1",
            tg_id,
            wallet,
        )
