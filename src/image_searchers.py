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
