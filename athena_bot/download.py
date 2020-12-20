import aiohttp
import asyncio
import sys
from athena_bot.utils import to_camel

HEROES = ['ana', 'ashe','bastion', 'baptiste', 'brigitte','dva', 'echo', 'genji','hanzo','junkrat','lucio','mccree','mei','mercy','orisa','pharah','reaper','reinhardt','roadhog','soldier76','sombra','symmetra','torbjorn','tracer','widowmaker','winston','zarya','zenyatta', 'sigma', 'doomfist', 'soldier-76', 'wrecking-ball', 'moira']

async def download(hero):
    url = f'https://d1u1mce87gyfbn.cloudfront.net/hero/{hero}/career-portrait.png'
    hero_camel = to_camel(hero)
    path = f'./assets/images/{hero_camel}.png'
    async with aiohttp.ClientSession() as client:
        try:
            async with client.get(url) as res:
                assert res.status == 200
                image_to_cache = await res.read()
                with open(path, 'wb') as image_file:
                    image_file.write(image_to_cache)
                return True
        except AssertionError as e:
            return None

async def download_all():
    for hero in HEROES:
        await download(hero)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(download(sys.argv[1]))
    else:
        asyncio.run(download_all())