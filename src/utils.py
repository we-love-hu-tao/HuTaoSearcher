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
import re
from typing import Literal

import aiohttp
from loguru import logger
from vkbottle import API, Callback, Keyboard
from vkbottle import KeyboardButtonColor as Color
from vkbottle import PhotoWallUploader, VKAPIError
from vkbottle.tools import PhotoMessageUploader

from config import CHARACTER_RENAMINGS, HU_TAO_RUSSIAN_TAG, IGNORE_TAGS, RERUN_DAY_SEARCH_RE
from db import (
    get_post,
    get_post_attachment,
    get_posts,
    get_search_posts,
    save_uploaded_attachment
)
from enums import PostAction


async def img_url_to_bytes(url: str) -> bytes:
    # Convert an image URL to a byte array
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()


async def get_attachment(
    uploader: PhotoMessageUploader, peer_id: int, url: str, post_id: int
) -> str:
    post_attachment = await get_post_attachment(post_id)
    if post_attachment:
        logger.info(f'Attachment for post {post_id} already exists in db')
        return post_attachment

    # Uploading image as an attachment and saving it in the database
    logger.info(f'Uploading new attachment for post {post_id}')
    image_bytes = await img_url_to_bytes(url)
    photo = await uploader.upload(
        file_source=image_bytes,
        peer_id=peer_id
    )
    await save_uploaded_attachment(post_id, photo)
    return photo


async def upload_wall_photo(
    uploader: PhotoWallUploader, url: str
) -> str:
    # Uploading image as a wall photo
    logger.info(f"Uploading new wall photo from this url: {url}")
    image_bytes = await img_url_to_bytes(url)
    photo = await uploader.upload(image_bytes)
    return photo


async def run_search(
    uploader: PhotoMessageUploader, peer_id: int, search_id: int, offset: int = 0
) -> dict:
    try:
        show_post_id = (await get_search_posts(search_id))[offset]
    except IndexError:
        end_kbd = (
            Keyboard(inline=True)
            .add(
                Callback(
                    '✅ Закончить поиск',
                    payload={'cmd': PostAction.END_SEARCH.value, 'search_id': search_id}
                )
            )
        ).get_json()
        return {
            "message": "🚩 Вы просмотрели все арты!",
            "photo": None,
            "keyboard": end_kbd,
        }

    show_post = await get_post(show_post_id)

    try:
        photo = await get_attachment(uploader, peer_id, show_post['preview_url'], show_post['id'])
    except VKAPIError[100] as e:
        # ? This is a very random error that I don't
        # ? even know why it happens or how to fix it...
        logger.info(f"Couldn't upload an image: {e}")
        photo = None

    msg = (
        f'🎨 Арт от {show_post["artist"]}\n'
        f'Пост на Danbooru: {show_post["url"]}\n'
        f'Источник: {show_post["source"]}\n'
        f'Персонажи: {show_post["characters"]}\n'
    )
    rate_kbd = (
        Keyboard(inline=True)
        .add(
            Callback(
                '✅ Запостить/В отложку',
                payload={
                    'cmd': PostAction.GOOD_POST.value,
                    'post_id': show_post['id'],
                    'search_id': search_id,
                    'new_offset': offset+1,
                },
            ),
            color=Color.POSITIVE,
        )
        .add(
            Callback(
                '❌ Удалить',
                payload={
                    'cmd': PostAction.DELETE_POST.value,
                    'post_id': show_post['id'],
                    'search_id': search_id,
                    'new_offset': offset+1,
                },
            ),
            color=Color.NEGATIVE,
        )
        .row()
        .add(
            Callback(
                '❓ Я хз',
                payload={
                    'cmd': PostAction.UNSURE_POST.value,
                    'post_id': show_post['id'],
                    'search_id': search_id,
                    'new_offset': offset+1,
                },
            ),
            color=Color.PRIMARY,
        )
        .row()
        .add(
            Callback(
                '⏭ Закончить поиск',
                payload={'cmd': PostAction.END_SEARCH.value, 'search_id': search_id}
            ),
            color=Color.SECONDARY,
        )
    ).get_json()
    return {
        "message": msg,
        "photo": photo,
        "keyboard": rate_kbd,
    }


async def get_modified_from_search(
    search_id: int,
    include_only: Literal['no_rating', 'to_post', 'deleted'] | None = None
) -> list[dict]:
    # This gets all post info, not only ids. Might be useful in the future.
    search_post_ids = await get_search_posts(search_id)
    posts = await get_posts()

    modified_posts = []
    if include_only:
        for post in posts:
            if post['id'] in search_post_ids and post['status'] == include_only:
                modified_posts.append(post)
    else:
        for post in posts:
            if post['id'] in search_post_ids and post['status'] != 'no_rating':
                modified_posts.append(post)

    return modified_posts


def hu_tao_sort(character: str):
    if character == "HuTao":
        return (0, character)
    elif character == "ХуТао":
        return (1, character)
    else:
        return (2, character)


def characters_to_tags(characters: str) -> str:
    """
    Converts Genshin Impact character Danbooru-styled tags to normal tags.
    This also sorts them, so Hu Tao is always first, just like she is at anything.
    >>> characters_to_tags("keqing_(genshin_impact) hu_tao_(genshin_impact)")
    >>> "#HuTao #ХуТао #Keqing"
    """
    # Removing all the unnecessary tags
    characters_list = characters.split()
    characters_list = [character for character in characters_list if character not in IGNORE_TAGS]
    characters = ' '.join(characters_list)

    # Making Danbooru-style tags look like normal tags
    characters = characters.replace('_(genshin_impact)', '')
    characters = characters.title()
    characters = characters.replace('_', '')
    characters_list = characters.split()
    characters_list = [
        CHARACTER_RENAMINGS.get(character) or character for character in characters_list
    ]
    for i, character in enumerate(characters_list):
        if character != 'HuTao':
            continue

        # Adding Russian variant right next to the original one
        characters_list.insert(i+1, HU_TAO_RUSSIAN_TAG)
        break

    characters_sorted_list = sorted(characters_list, key=hu_tao_sort)
    characters = ' '.join('#'+word for word in characters_sorted_list)
    return characters


async def get_rerun_day(api: API, group_id: int, search_in=20) -> int | None:
    last_posts_request = await api.wall.get(owner_id=-group_id, count=search_in)
    print(last_posts_request)
    last_posts = last_posts_request.items
    for post in last_posts:
        try:
            post_text = post.text
            re_match = re.search(RERUN_DAY_SEARCH_RE, post_text)
            day = int(re_match.group(1))
            return day
        except AttributeError:
            logger.info(f"Couldn't find rerun day in post {post}, trying next one")
            continue


def create_text(next_rerun_day: int, artist: str, characters: str):
    msg = (
        f"{next_rerun_day} без рерана Ху Тао\n\nАвтор: {artist}"
        f"\n{characters} #genshinimpact #genshin_impact"
    )
    return msg


async def main():
    search_id = 1
    modified = await get_modified_from_search(search_id)
    print(modified)


if __name__ == '__main__':
    asyncio.run(main())
