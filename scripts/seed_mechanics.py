import asyncio
import os
import asyncpg


MECHANICS = [
    ("+256701234567", "John Okello", "Kampala Central", True, 4.8, 156),
    ("+256702345678", "Peter Ssemwogerere", "Nakawa", True, 4.5, 98),
    ("+256703456789", "James Mugisha", "Makindye", False, 4.2, 45),
    ("+256704567890", "David Lubega", "Ntinda", True, 4.9, 201),
    ("+256705678901", "Moses Kasule", "Wandegeya", False, 3.8, 23),
]


async def seed():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mechanics (
                id SERIAL PRIMARY KEY,
                phone TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                location TEXT,
                is_verified BOOLEAN DEFAULT FALSE,
                rating NUMERIC(3,1) DEFAULT 0,
                jobs_completed INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        )

        for phone, name, location, is_verified, rating, jobs_completed in MECHANICS:
            await conn.execute(
                """
                INSERT INTO mechanics (phone, name, location, is_verified, rating, jobs_completed)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (phone) DO UPDATE
                  SET name = EXCLUDED.name,
                      location = EXCLUDED.location,
                      is_verified = EXCLUDED.is_verified,
                      rating = EXCLUDED.rating,
                      jobs_completed = EXCLUDED.jobs_completed;
                """,
                phone,
                name,
                location,
                is_verified,
                rating,
                jobs_completed,
            )

        print("Seeded mechanics successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())

