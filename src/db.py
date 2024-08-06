import asyncio
from typing import Literal

import aiosqlite
import msgspec

from config import DB_PATH

SQL_CREATE_POSTS_TABLE = """CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY UNIQUE,
    post_id INTEGER NOT NULL UNIQUE,
    status TEXT DEFAULT "no_rating" NOT NULL
    -- Possible status values: 'no_rating', 'to_post', 'deleted'
);"""
SQL_CREATE_SEARCHES_TABLE = """CREATE TABLE IF NOT EXISTS searches (
    search_id INTEGER PRIMARY KEY UNIQUE,
    search_posts TEXT NOT NULL
);"""
SQL_VK_ATTACHMENTS_TABLE = """CREATE TABLE IF NOT EXISTS vk_attachments (
    id INTEGER PRIMARY KEY UNIQUE,
    attachment TEXT NOT NULL
);"""


async def create_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(SQL_CREATE_POSTS_TABLE)
        await db.execute(SQL_CREATE_SEARCHES_TABLE)
        await db.execute(SQL_VK_ATTACHMENTS_TABLE)
        await db.commit()


async def add_posts(
    post_ids: list[int] | int,
    status: Literal['no_rating', 'to_post', 'deleted'] = 'no_rating'
) -> None:
    if isinstance(post_ids, int):
        post_ids = [post_ids]

    multiple_columns = [(post_id, status) for post_id in post_ids]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            'INSERT INTO posts (post_id, status) VALUES (?, ?);',
            multiple_columns
        )
        await db.commit()


async def update_posts_status(
    post_ids: list[int] | int,
    status: Literal['no_rating', 'to_post', 'deleted'] = 'no_rating'
) -> None:
    if isinstance(post_ids, int):
        post_ids = [post_ids]

    multiple_columns = [(status, post_id) for post_id in post_ids]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            'UPDATE posts SET status = ? WHERE post_id = ?;',
            multiple_columns
        )
        await db.commit()


async def get_posts() -> list[tuple[int, str]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT post_id, status FROM posts;')
        return await cursor.fetchall()


async def get_post(post_id) -> tuple:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT post_id, status FROM posts WHERE post_id = ?;', (post_id,)
        )
        return await cursor.fetchone()


async def posts_exists(post_id) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT post_id FROM posts WHERE post_id = ?;', (post_id,))
        return (await cursor.fetchone()) is not None


async def create_search(posts: list[dict]) -> int:
    # Returns the search id of the newly created search
    posts_json = msgspec.json.encode(posts)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            'INSERT INTO searches (search_posts) VALUES (?) RETURNING search_id;',
            (posts_json,)
        )
        search_id_row = await cur.fetchone()
        search_id = search_id_row[0]
        await db.commit()
    return search_id


async def get_search_posts(search_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT search_posts FROM searches WHERE search_id = ?;',
            (search_id,)
        )
        results = await cursor.fetchone()
    posts = msgspec.json.decode(results[0])
    return posts


async def delete_search(search_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM searches WHERE search_id = ?;', (search_id,))
        await db.commit()


async def save_uploaded_attachment(post_id: int, attachment_string: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO vk_attachments (id, attachment) VALUES (?, ?)",
            (post_id, attachment_string,)
        )
        await db.commit()


async def get_post_attachment(post_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT attachment FROM vk_attachments WHERE id = ?;',
            (post_id,)
        )
        results = await cursor.fetchone()
        return results


async def main():
    # Example usage
    await create_db()
    search_id = await create_search([1, 2])
    print(f"New search id: {search_id}")

    posts = await get_search_posts(search_id)
    print(f"Posts in newly created search: {posts}")


if __name__ == '__main__':
    asyncio.run(main())
