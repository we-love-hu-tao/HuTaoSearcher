# Hu Tao Art Searcher
# Copyright (C) 2024  F1zzTao

# This file is part of Hu Tao Art Searcher.
# Hu Tao Art Searcher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Hu Tao Art Searcher.  If not, see <https://www.gnu.org/licenses/>.

# You may contact F1zzTao by this email address: timurbogdanov2008@gmail.com

import asyncio
from typing import Literal

import aiosqlite

from config import DB_PATH

SQL_CREATE_POSTS_TABLE = """CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY UNIQUE,
    status TEXT DEFAULT "no_rating" NOT NULL,
    preview_url TEXT NOT NULL,
    file_url TEXT NOT NULL,
    artist TEXT NOT NULL,
    characters TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT NOT NULL
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
    posts: list[dict] | dict,
    status: Literal['no_rating', 'to_post', 'deleted'] = 'no_rating'
) -> None:
    if isinstance(posts, dict):
        posts = [posts]

    multiple_columns = []
    for post in posts:
        multiple_columns.append(
            (
                post['id'],
                status,
                post['preview_url'],
                post['file_url'],
                post['artist'],
                post['characters'],
                post['url'],
                post['source'],
            )
        )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            'INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
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
            'UPDATE posts SET status = ? WHERE id = ?;',
            multiple_columns
        )
        await db.commit()


async def get_posts() -> list[tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM posts;')
        result = await cursor.fetchall()

    posts = []
    for post in result:
        # TODO: Make this a msgspec object
        new_post = {
            'id': post[0],
            'status': post[1],
            'preview_url': post[2],
            'file_url': post[3],
            'artist': post[4],
            'characters': post[5],
            'url': post[6],
            'source': post[7],
        }
        posts.append(new_post)
    return posts


async def get_post(post_id) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT * FROM posts WHERE id = ?;', (post_id,)
        )
        result = await cursor.fetchone()

    # TODO: Make this a msgspec object
    post = {
        'id': result[0],
        'status': result[1],
        'preview_url': result[2],
        'file_url': result[3],
        'artist': result[4],
        'characters': result[5],
        'url': result[6],
        'source': result[7],
    }
    return post


async def posts_exists(post_id) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id FROM posts WHERE id = ?;', (post_id,))
        return (await cursor.fetchone()) is not None


async def create_search(post_ids: list[int]) -> int:
    # Returns the search id of the newly created search
    post_ids = [str(post_id) for post_id in post_ids]
    posts_formatted = ','.join(post_ids)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            'INSERT INTO searches (search_posts) VALUES (?) RETURNING search_id;',
            (posts_formatted,)
        )
        search_id_row = await cur.fetchone()
        search_id = search_id_row[0]
        await db.commit()
    return search_id


async def get_search_posts(search_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT search_posts FROM searches WHERE search_id = ?;',
            (search_id,)
        )
        results = await cursor.fetchone()
    posts_str = results[0].split(',')
    posts = [int(post) for post in posts_str]
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
    a = await get_posts()
    print(a)


if __name__ == '__main__':
    asyncio.run(main())
