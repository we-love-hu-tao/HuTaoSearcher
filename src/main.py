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
import datetime
import logging
import time

from loguru import logger
from vkbottle import Callback, GroupEventType, Keyboard
from vkbottle import KeyboardButtonColor as Color
from vkbottle import User
from vkbottle.bot import Bot, Message, MessageEvent, rules
from vkbottle.tools import PhotoMessageUploader, PhotoWallUploader

from config import (
    ADMIN_IDS,
    GROUP_ID,
    HU_TAO_QUERY,
    VK_API_TOKEN,
    VK_USER_API_TOKEN,
    post_interval
)
from db import (
    add_posts,
    create_db,
    create_search,
    delete_search,
    get_posts,
    update_posts_status
)
from enums import PostAction, SearchAction
from image_searchers import DanbooruSearcher
from utils import (
    characters_to_tags,
    create_text,
    get_last_posts,
    get_last_rerun_day,
    get_modified_from_search,
    get_rerun_day,
    run_search,
    set_last_rerun_day,
    upload_wall_photo
)

logging.getLogger('aiosqlite').setLevel(logging.INFO)

bot = Bot(VK_API_TOKEN)
user = User(VK_USER_API_TOKEN)
photo_msg_upl = PhotoMessageUploader(bot.api)
photo_wall_upl = PhotoWallUploader(user.api)
dan = DanbooruSearcher()
bot.labeler.vbml_ignore_case = True


@bot.on.private_message(
    text=('.hu tao', '.ху тао', '.hu tao <custom_search>', '.ху тао <custom_search>')
)
async def search_tao_handler(message: Message, custom_search: str | None = None):
    if message.from_id not in ADMIN_IDS:
        return

    msg_to_edit = await message.answer('🔎 Ищем, пожалуйста подождите...')

    existing_posts = await get_posts()
    reviewed_posts_ids = [post['id'] for post in existing_posts if post['status'] != 'no_rating']
    new_posts = await dan.search(custom_search or HU_TAO_QUERY, limit=10)
    show_posts = []
    for post in new_posts:
        if post['id'] in reviewed_posts_ids:
            continue

        try:
            formatted_characters = characters_to_tags(post['tag_string_character'])
            show_posts.append(
                {
                    'id': post['id'],
                    'preview_url': post['large_file_url'],
                    'file_url': post['file_url'],
                    'artist': post['tag_string_artist'],
                    'characters': formatted_characters,
                    'url': post['post_url'],
                    'source': post['source'],
                }
            )
        except KeyError:
            # Some posts don't have some of the keys for some reason
            continue
        logger.info(f'Found new post (by {post["tag_string_artist"]}): {post["post_url"]}')

    await add_posts(show_posts)

    if not show_posts:
        await bot.api.messages.edit(
            peer_id=message.peer_id,
            conversation_message_id=msg_to_edit.conversation_message_id,
            message=(
                '🤔 Новых артов с Ху Тао не нашлось! Все просмотренные арты можно'
                ' найти с помощью команды ".Ху Тао история" (пока не работает)'
            )
        )
        return

    post_ids = [post['id'] for post in show_posts]
    search_id = await create_search(post_ids)
    completed_search = await run_search(photo_msg_upl, message.peer_id, search_id)

    await bot.api.messages.edit(
        peer_id=message.peer_id,
        conversation_message_id=msg_to_edit.conversation_message_id,
        message=completed_search['message'],
        attachment=completed_search['photo'],
        keyboard=completed_search['keyboard']
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', PostAction.GOOD_POST.value),
        ('post_id', int),
        ('search_id', int),
        ('new_offset', int)
    ])
)
async def good_post_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    post_id, search_id, new_offset = payload['post_id'], payload['search_id'], payload['new_offset']
    await update_posts_status(post_id, 'to_post')

    search_results = await run_search(photo_msg_upl, event.peer_id, search_id, new_offset)
    await event.edit_message(
        peer_id=event.peer_id,
        message=search_results['message'],
        attachment=search_results['photo'],
        keyboard=search_results['keyboard']
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', PostAction.DELETE_POST.value),
        ('post_id', int),
        ('search_id', int),
        ('new_offset', int)
    ])
)
async def delete_post_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    post_id, search_id, new_offset = payload['post_id'], payload['search_id'], payload['new_offset']
    await update_posts_status(post_id, 'deleted')

    search_results = await run_search(photo_msg_upl, event.peer_id, search_id, new_offset)
    await event.edit_message(
        peer_id=event.peer_id,
        message=search_results['message'],
        attachment=search_results['photo'],
        keyboard=search_results['keyboard']
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', PostAction.UNSURE_POST.value),
        ('post_id', int),
        ('search_id', int),
        ('new_offset', int)
    ])
)
async def unsure_post_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    search_id, new_offset = payload['search_id'], payload['new_offset']

    search_results = await run_search(photo_msg_upl, event.peer_id, search_id, new_offset)
    await event.edit_message(
        peer_id=event.peer_id,
        message=search_results['message'],
        attachment=search_results['photo'],
        keyboard=search_results['keyboard']
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', PostAction.END_SEARCH.value),
        ('search_id', int)
    ])
)
async def end_search_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    search_id = payload['search_id']

    to_post = await get_modified_from_search(search_id, 'to_post')
    to_post_count = len(to_post)

    confirmation_kbd = (
        Keyboard(inline=True)
        .add(
            Callback(
                '✅ Запостить/отложить посты',
                payload={'cmd': SearchAction.POST.value, 'search_id': search_id}
            ),
            Color.POSITIVE
        )
        .row()
        .add(
            Callback(
                '❌ Отмена',
                payload={'cmd': SearchAction.CANCEL.value, 'search_id': search_id}
            ),
            Color.NEGATIVE
        )
    ).get_json()

    ending = ''
    if to_post_count >= 2 and to_post_count <= 4:
        ending = 'а'
    elif to_post_count >= 5:
        ending = 'ов'

    await event.edit_message(
        peer_id=event.peer_id,
        message=(
            f'➡️ Вы собираетесь запостить или оставить в отложке {to_post_count} пост{ending}.'
            f' На данный момент в боте установлен интервал постов в {post_interval} секунд.'
            ' Продолжить?',
        ),
        keyboard=confirmation_kbd
    )


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', SearchAction.POST.value),
        ('search_id', int)
    ])
)
async def post_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    search_id = payload['search_id']

    to_post = await get_modified_from_search(search_id, 'to_post', sort=True)
    to_post_ids = [post['id'] for post in to_post]
    to_post_count = len(to_post_ids)
    await event.edit_message('⏳ Постим посты...')

    await delete_search(search_id)
    await update_posts_status(to_post_ids, 'deleted')

    posts = await get_last_posts(user.api, GROUP_ID)
    next_rerun_day = get_rerun_day(posts) + 1
    last_post_time = posts[0]["date"]
    post_failed = 0
    for post in to_post:
        attachment = await upload_wall_photo(photo_wall_upl, post['file_url'])
        if not attachment:
            post_failed += 1
            continue
        text = create_text(next_rerun_day, post['artist'], post['characters'])
        next_rerun_day += 1

        # Determining when to post this post
        current_time = int(time.time())
        if last_post_time + post_interval < current_time:
            # [POST_INTERVAL] seconds has passed since last post
            publish_date = None
        else:
            # [POST_INTERVAL] seconds has not passed since last post
            difference = current_time-last_post_time
            publish_date = current_time+post_interval-difference
        last_post_time = publish_date or current_time

        await user.api.wall.post(
            owner_id=-GROUP_ID,
            from_group=True,
            message=text,
            attachments=[attachment],
            publish_date=publish_date,
        )
        await asyncio.sleep(2)

    ending = ''
    if to_post_count >= 2 and to_post_count <= 4:
        ending = 'а'
    elif to_post_count >= 5:
        ending = 'ов'

    msg = (
        f'✅ Успешно запостили или оставили в отложке {to_post_count} пост{ending}!'
        ' Напишите ".Ху Тао" чтобы снова начать поиск!'
    )
    if post_failed:
        msg += f"\n⚠️ Некоторые посты не удалось запостить ({post_failed})."

    await event.edit_message(msg)


@bot.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    rules.PayloadMapRule([
        ('cmd', SearchAction.CANCEL.value),
        ('search_id', int)
    ])
)
async def cancel_search_handler(event: MessageEvent):
    if event.user_id not in ADMIN_IDS:
        return

    payload = event.get_payload_json()
    search_id = payload['search_id']

    # Defaulting every post's status from search
    to_post = await get_modified_from_search(search_id)
    to_post_ids = [post['id'] for post in to_post]
    await update_posts_status(to_post_ids, 'no_rating')

    await delete_search(search_id)

    await event.edit_message(
        '✋ Вы отменили поиск вместе со всеми изменениями. '
        'Напишите ".Ху Тао" чтобы снова начать поиск!'
    )


@bot.on.private_message(text=('.реран', '!реран'))
async def rerun_info_handler(message: Message):
    if message.from_id not in ADMIN_IDS:
        return

    try:
        last_rerun_date = await get_last_rerun_day()
    except FileNotFoundError:
        return (
            '❌ Похоже, что последний день рерана Ху Тао ещё не установлен. Напишите'
            ' ".установить реран"'
        )
    today_date = datetime.date.today()
    no_rerun_days = (today_date - last_rerun_date).days
    msg = (
        f'🕒 Последний реран Ху Тао: {str(last_rerun_date)}\n'
        f'⏳ Это уже {no_rerun_days} день без рерана Ху Тао.'
    )
    return msg


@bot.on.private_message(text=('.установить реран', '!установить реран'))
async def set_rerun_day_info_handler(message: Message):
    if message.from_id not in ADMIN_IDS:
        return

    return 'Чтобы установить последний день рерана Ху Тао, укажите дату в формате "ГГГГ-ММ-ДД"'


@bot.on.private_message(text=('.установить реран <date_str>', '!установить реран <date_str>'))
async def set_rerun_day_handler(message: Message, date_str: str):
    if message.from_id not in ADMIN_IDS:
        return

    try:
        last_rerun_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return (
            '❌ Неверный формат даты. Напишите ".установить реран" без параметров, чтобы узнать,'
            ' как установить дату.'
        )

    await set_last_rerun_day(last_rerun_date)
    return '✅ Готово!'


if __name__ == '__main__':
    bot.loop_wrapper.on_startup.append(create_db())
    bot.run_forever()
