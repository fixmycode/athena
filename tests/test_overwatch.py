from athena_bot.overwatch import Overwatch
import asyncio

battletags = ['fixmycode#1699', 'Masterwolf#11405', 'TreeboyDave#21401', 'Cellophane#11706', 'Kozak#21746']

async def test_image():
    o = Overwatch()
    for tag in battletags:
        d = await o.get_stats(tag)
        await o.build_profile_image(d)

asyncio.run(test_image())