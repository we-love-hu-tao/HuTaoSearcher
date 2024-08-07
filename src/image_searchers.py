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

import booru
import msgspec


class DanbooruSearcher:
    def __init__(self):
        self.dan = booru.Danbooru()
        self.decoder = msgspec.json.Decoder()

    async def search(self, query: str, block: str = '', limit: int = 100) -> list[dict]:
        res = await self.dan.search(query=query, block=block, limit=limit, random=False)
        return self.decoder.decode(res)


async def main():
    # Example usage
    dan = DanbooruSearcher()
    # posts = await dan.search('hu_tao_(genshin_impact) 2girls rating:g')
    posts = await dan.search('id:7946030')
    print(posts)


if __name__ == '__main__':
    asyncio.run(main())
