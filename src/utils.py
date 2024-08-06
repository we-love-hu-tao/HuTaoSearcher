import aiohttp
from vkbottle import Callback, Keyboard, VKAPIError
from vkbottle import KeyboardButtonColor as Color
from vkbottle.tools import PhotoMessageUploader

from db import get_search_posts, save_uploaded_attachment, get_posts, get_post_attachment
from typing import Literal
from enums import PostAction
from loguru import logger


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
        logger.info(f"Attachment for post {post_id} already exists in db")
        return post_attachment

    # Uploading image as an attachment and saving it in the database
    logger.info(f"Uploading new attachment for post {post_id}")
    image_bytes = await img_url_to_bytes(url)
    photo = await uploader.upload(
        file_source=image_bytes,
        peer_id=peer_id
    )
    await save_uploaded_attachment(post_id, photo)
    return photo


async def run_search(
    uploader: PhotoMessageUploader, peer_id: int, search_id: int, offset: int = 0
) -> dict:
    try:
        show_post = (await get_search_posts(search_id))[offset]
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
) -> list[int]:
    search_posts = await get_search_posts(search_id)
    search_posts_ids = [post['id'] for post in search_posts]

    posts = await get_posts()
    posts_dict = dict(posts)

    if include_only:
        to_post = [post for post in search_posts_ids if posts_dict.get(post) == include_only]
    else:
        to_post = [post for post in search_posts_ids if posts_dict.get(post) != 'no_rating']
    return to_post

    """
    # This gets all post info, not only ids. Might be useful in the future.
    search_posts = await get_search_posts(search_id)
    posts = await get_posts()

    all_modified_posts = {post[0] for post in posts if post[1] != 'no_rating'}
    search_modified = [post for post in search_posts if post['id'] in all_modified_posts]

    return search_modified
    """
