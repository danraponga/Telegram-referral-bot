from asyncpg import Pool


async def prepare_db(pool: Pool):
    async with pool.acquire() as db:
        await db.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'locale_enum') THEN
                    CREATE TYPE locale_enum AS ENUM ('ru', 'en');
                END IF;
            END
            $$;
            """
        )

        await db.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reward_enum') THEN
                    CREATE TYPE reward_enum AS ENUM (
                        'registration', 'checkin', 'subscription', 'invitation', 'referrer_part', 'checkin_gap_hours'
                    );
                END IF;
            END
            $$;
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                username TEXT,
                points FLOAT DEFAULT 10.0,
                ref_code TEXT UNIQUE,
                join_date TIMESTAMPTZ DEFAULT NOW(),
                last_check_in TIMESTAMPTZ,
                language locale_enum DEFAULT 'en',
                wallet TEXT DEFAULT NULL
            );
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id INT,
                referrer_id INT,
                FOREIGN KEY (referral_id) REFERENCES users(user_id),
                FOREIGN KEY (referrer_id) REFERENCES users(user_id)
            );
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                channel_id SERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                required BOOL
            );            
        """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_channels (
            user_id INT,
            channel_id INT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rewards(
                reward_id SERIAL PRIMARY KEY,
                reward_type reward_enum UNIQUE,
                value FLOAT
            );
            """
        )

        count = await db.fetchval("SELECT COUNT(*) FROM rewards;")
        if count == 0:
            await db.execute(
                """
                INSERT INTO rewards (reward_type, value)
                VALUES
                    ('registration', 10),
                    ('checkin', 5),
                    ('subscription', 10),
                    ('invitation', 50),
                    ('referrer_part', 0.1),
                    ('checkin_gap_hours', 24);
                """
            )
        await db.close()
