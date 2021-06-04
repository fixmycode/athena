import os
import aiohttp
import time
import re
import logging
import glob
import random
from datetime import datetime
from contextlib import asynccontextmanager, contextmanager
from PIL import Image, ImageDraw, ImageFont
from athena_bot import utils
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def rounded_rectangle(self: ImageDraw, xy, corner_radius, fill=None, outline=None):
    upper_left_point = xy[0]
    bottom_right_point = xy[1]
    self.pieslice([upper_left_point, (upper_left_point[0] + corner_radius * 2, upper_left_point[1] + corner_radius * 2)],
        180, 270, fill=fill, outline=outline
    )
    self.pieslice([(bottom_right_point[0] - corner_radius * 2, bottom_right_point[1] - corner_radius * 2), bottom_right_point],
        0, 90, fill=fill, outline=outline
    )
    self.pieslice([(upper_left_point[0], bottom_right_point[1] - corner_radius * 2), (upper_left_point[0] + corner_radius * 2, bottom_right_point[1])],
        90, 180, fill=fill, outline=outline
    )
    self.pieslice([(bottom_right_point[0] - corner_radius * 2, upper_left_point[1]), (bottom_right_point[0], upper_left_point[1] + corner_radius * 2)],
        270, 360, fill=fill, outline=outline
    )
    self.rectangle([
        (upper_left_point[0], upper_left_point[1] + corner_radius),
        (bottom_right_point[0], bottom_right_point[1] - corner_radius)],
        fill=fill, outline=fill
    )
    self.rectangle([
        (upper_left_point[0] + corner_radius, upper_left_point[1]),
        (bottom_right_point[0] - corner_radius, bottom_right_point[1])],
        fill=fill, outline=fill
    )
    #self.line([(upper_left_point[0] + corner_radius, upper_left_point[1]), (bottom_right_point[0] - corner_radius, upper_left_point[1])], fill=outline)
    #self.line([(upper_left_point[0] + corner_radius, bottom_right_point[1]), (bottom_right_point[0] - corner_radius, bottom_right_point[1])], fill=outline)
    #self.line([(upper_left_point[0], upper_left_point[1] + corner_radius), (upper_left_point[0], bottom_right_point[1] - corner_radius)], fill=outline)
    #self.line([(bottom_right_point[0], upper_left_point[1] + corner_radius), (bottom_right_point[0], bottom_right_point[1] - corner_radius)], fill=outline)


class Overwatch:
    BASE_URL='https://ow-api.com/v1/stats'
    CACHE_FILE=os.environ.get('OVERWATCH_DATA', './overwatch.p')
    IMG_CACHE=os.environ.get('OVERWATCH_IMAGES', './cache')
    CACHE_EXPIRE=os.environ.get('OVERWATCH_EXPIRE', 60)
    HERO_IMAGES='./assets/images/'
    FONT_FILES='./assets/fonts/'
    BG_IMAGES='./assets/backgrounds/'

    def __init__(self):
        logger.info('Initializing Overwatch')
        self.cache = utils.read_datafile(self.CACHE_FILE)
        self.font_cache = {}

    async def get_stats(self, battletag, refresh=False):
        if not refresh:
            cached_bt = self.cache.get(battletag)
            if cached_bt and self.__check_expiration(cached_bt):
                logger.debug(f'cache hit on {battletag} stats')
                return cached_bt
        async with aiohttp.ClientSession() as client:
            logger.debug(f'getting fresh {battletag} stats')
            try:
                async with client.get(f'{self.BASE_URL}/pc/us/{battletag.replace("#","-")}/complete') as res:
                    assert res.status == 200
                    fresh_data = await res.json()
                    fresh_data.update({'accessed': datetime.now()})
                    self.cache.update({battletag: fresh_data})
                    utils.write_datafile(self.CACHE_FILE, self.cache)
                    return fresh_data
            except AssertionError as e:
                logger.info(f'error reading stats for {battletag}')
                return False
    

    async def full_refresh(self, forced=False):
        for tag in self.cache.keys():
            await self.get_stats(tag, refresh=forced)
    

    def find_best(self, role):
        role = 'support' if role in ['healer', 'support'] else role
        role = 'damage' if role in ['dps', 'damage dealer'] else role
        role = 'tank' if role in ['tank', 'shield'] else role
        role_list = []
        for battletag, data in self.cache.items():
            ratings = data.get('ratings')
            if not ratings:
                continue
            for rating in ratings:
                if rating['role'] == role:
                    role_list.append((battletag, rating['level']))
                    break
        if not role_list:
            return None
        role_list.sort(key=lambda t: -t[1])
        if len(role_list) == 1:
            return role_list[0][0]
        result = {}
        for i in range(len(role_list)):
            tag_a, level_a = role_list[i]
            tag_b, level_b = role_list[i+1]
            if level_a > level_b:
                return [tag_a,]
            result.update({tag_a, tag_b})
            if i+1 < len(role_list):
                i += 1
        return list(result)
            

    def get_font(self, font_name, size):
        try:
            font = self.font_cache[(font_name, size)]
        except KeyError as e:
            logger.debug(f'font {font_name} not found, loading to cache')
            font = ImageFont.truetype(os.path.join(self.FONT_FILES, font_name), size)
            self.font_cache.update({(font_name, size): font})
        return font

    def __check_expiration(self, cached_data):
        now = datetime.now()
        accessed = cached_data.get('accessed', False)
        return accessed and now < accessed + timedelta(minutes=self.CACHE_EXPIRE)

    def top_hero(self, data):
        if data['private']:
            return None
        games = [(k, int(v['timePlayed'].replace(':',''))) for k, v in data['quickPlayStats']['topHeroes'].items()]
        top = sorted(games, key=lambda x: x[1], reverse=True) #HAAAAA
        return top[0][0]

    async def __cached_image(self, url, key=None, expire=None, ext='png') -> Image:
        if not key:
            match = re.search(r'([a-zA-Z0-9-]*\.'+ext+')$', url)
            key = match.groups()[0]
        path = os.path.join(self.IMG_CACHE, key + '.' + ext)
        try:
            if expire:
                file_time = os.path.getmtime(path)  
                is_expired = ((time.time() - file_time) / 3600 > 24*expire)
                if is_expired:
                    raise FileNotFoundError()
            return Image.open(path)
        except FileNotFoundError as e:
            logger.debug(f'image {key} not found, loading to cache')
            if not url:
                return
            async with aiohttp.ClientSession() as client:
                try:
                    async with client.get(url) as res:
                        assert res.status == 200
                        image_to_cache = await res.read()
                        with open(path, 'wb') as image_file:
                            image_file.write(image_to_cache)
                        return Image.open(path)
                except AssertionError as e:
                    logger.debug(f'error downloading image {key}')
                    return None
        return None

    def line_size(self, line, font:ImageFont):
        bbox = font.getmask(line).getbbox()
        return (bbox[2], bbox[3])

    @asynccontextmanager
    async def get_cached_image(self, url, key=None, expire=None, ext='png'):
        image = await self.__cached_image(url, key, expire, ext)
        try:
            yield image
        finally:
            if image:
                image.close()

    @asynccontextmanager
    async def rating_badge(self, rating):
        im = Image.new('RGBA', (80, 25), 'rgba(0,0,0,0)')
        async with self.get_cached_image(rating['roleIcon'], key=rating['role'], expire=30) as role_icon, self.get_cached_image(rating['rankIcon'], expire=30) as rank_icon:
            font = self.get_font('RobotoCondensed-Bold.ttf', 15)
            im.alpha_composite(role_icon.resize((15, 15)), (4, 6))
            d = ImageDraw.Draw(im)
            d.text((24, 5), str(rating['level']), font=font, fill='white')
            im.alpha_composite(rank_icon.resize((20, 20)), (26 + self.line_size(str(rating['level']), font)[0], 4))
        try:
            yield im
        finally:
            im.close()

    @contextmanager
    def level_badge(self, level, prestige):
        BRONZE = ('white', '#9c4b30')
        SILVER = ('#2e2d46', '#c0c0c0')
        GOLD = ('#692e00', '#ffd700')
        PLATINUM = SILVER
        DIAMOND = ('#2e2d46', '#d1cded')
        HEIGHT = 25

        font = self.get_font('RobotoCondensed-Bold.ttf', 20)
        symbol = self.get_font('Symbola.otf', 20)
        mod_prestige = (prestige % 6)
        level_width = self.line_size(str(level), font)[0]

        color = BRONZE
        if prestige > 5:
            color = SILVER
        if prestige > 11:
            color = GOLD
        if prestige > 17:
            color = PLATINUM
        if prestige > 23:
            color = DIAMOND
        if prestige > 29:
            mod_prestige = 5

        if mod_prestige > 0:
            width = level_width + self.line_size('★'*mod_prestige, symbol)[0] + 15
        else:
            width = level_width + 10
        im = Image.new('RGBA', (width, HEIGHT), 'rgba(0,0,0,0)')
        d = ImageDraw.Draw(im)

        f_color, bg_color = color
        rounded_rectangle(d, ((0, 0), (width-2, HEIGHT-2)), 7, fill=bg_color)
        d.text((5, 0), str(level), font=font, fill=f_color)

        if mod_prestige > 0:
            rounded_rectangle(d, ((level_width+10, 1), (width-3, HEIGHT-3)), 7, fill='white')
            d.rectangle(((level_width+10, 1), (width-10, HEIGHT-3)), fill='white')
            star_color = GOLD[1] if prestige > 16 else f_color if prestige > 5 else bg_color
            d.text((self.line_size(str(level), font)[0] + 11, -1), '★'*mod_prestige, font=symbol, fill=star_color)
        try:
            yield im
        finally:
            im.close()

    def total_stats(self, data, key):
        try:
            stats = data[key]['careerStats']['allHeroes']['game']
            games = stats['gamesPlayed']
            try:
                hours, minutes, secs = re.match(r'(\d+):(\d{2}):(\d{2})', stats['timePlayed']).groups()
                time = int(hours) + (int(minutes) / 60) + (int(secs) / 3600)
            except AttributeError as e:
                minutes, secs = re.match(r'(\d{2}):(\d{2})', stats['timePlayed']).groups()
                time = (int(minutes) / 60) + (int(secs) / 3600)
        except KeyError as e:
            games = 0
            time = 0
        return (games, time)
    
    @asynccontextmanager
    async def top_bar_image(self, data, width):
        im = Image.new('RGBA', (width, 70), (0,0,0,180))
        # draws the user icon
        icon_key = data['name'].replace('#', '-') + 'icon'
        async with self.get_cached_image(data['icon'], icon_key, 1) as icon_img:
            icon_img = icon_img.resize((50, 50))
            im.paste(icon_img, (10, 10))
        # draws name and number
        d = ImageDraw.Draw(im)
        name_fnt = self.get_font('RobotoCondensed-BoldItalic.ttf', 30)
        number_fnt = self.get_font('RobotoCondensed-Italic.ttf', 15)
        name, number = data['name'].split('#')
        d.text((70,10), name, font=name_fnt, fill=(255,255,255,255))
        d.text((68,40), '#'+number, font=number_fnt, fill=(255,255,255,128))
        # draws level badge
        with self.level_badge(data['level'], data['prestige']) as lv_img:
            im.alpha_composite(lv_img, (self.line_size(name, name_fnt)[0]+75, 15))
        try:
            yield im
        finally:
            im.close()

    @contextmanager
    def mid_bar_image(self, data, width):
        if data['private']:
            bar_color = (128,0,0, 180)
            bar_text = 'This profile is private'
        else:
            bar_color = (255,255,255,180)
            g_comp, t_comp = self.total_stats(data, 'competitiveStats')
            g_qp, t_qp = self.total_stats(data, 'quickPlayStats')
            bar_text = f'{g_comp + g_qp} Games / {int(t_comp + t_qp)} Hrs'
        im = Image.new('RGBA', (width, 24), bar_color)
        font = self.get_font('RobotoCondensed-Bold.ttf', 15)
        d = ImageDraw.Draw(im)
        d.text((10, 4), bar_text, font=font, fill='black')
        try:
            yield im
        finally:
            im.close()

    @contextmanager
    def background_img(self, width):
        images = glob.glob(os.path.join(self.BG_IMAGES, '*.jpg'))
        image_path = random.choice(images)
        im = Image.open(image_path)
        im.thumbnail((width, width))
        im = im.convert('RGBA')
        try:
            yield im
        finally:
            im.close()


    @asynccontextmanager
    async def bottom_bar_img(self, data, width):
        im = Image.new('RGBA', (width, 25), (0,0,0,180))
        x = 0
        for rating in data.get('ratings'):
            async with self.rating_badge(rating) as rim:
                im.alpha_composite(rim, (x, 0))
                x += rim.width
        try:
            yield im
        finally:
            im.close()

    @contextmanager
    def hero_image(self, hero):
        im = Image.open(os.path.join(self.HERO_IMAGES, hero + '.png'))
        im = im.resize((10 * im.width // 31, 10 * im.height // 31), Image.HAMMING)
        im = im.convert('RGBA')
        try:
            yield im
        finally:
            im.close()

    async def build_profile_image(self, data):
        width = 500
        im = Image.new('RGBA', (width, width), (0, 0, 0, 0))
        actual_height = 0
        with self.background_img(width) as bg_img:
            im.paste(bg_img, (0, -bg_img.height//4))
        async with self.top_bar_image(data, width) as top_img:
            im.alpha_composite(top_img, (0, 0))
            actual_height += top_img.height
            with self.mid_bar_image(data, width) as mid_img:
                im.alpha_composite(mid_img, (0, top_img.height))
                actual_height += mid_img.height
                if data.get('ratings'):
                    async with self.bottom_bar_img(data, width) as bot_img:
                        im.alpha_composite(bot_img, (0, top_img.height + mid_img.height))
                        actual_height += bot_img.height
        im = im.crop(((0,0, width, actual_height)))
        top_hero = self.top_hero(data)
        if top_hero:
            with self.hero_image(top_hero) as hero_image:
                height = max(hero_image.height, actual_height)
                final_image = Image.new('RGBA', (width, height), (0,0,0,0))
                final_image.alpha_composite(im, (0, height - im.height))
                final_image.alpha_composite(hero_image, (final_image.width - hero_image.width + 50, 0))
                im.close()
                im = final_image
        im.save(os.path.join(self.IMG_CACHE, f'badge-{data["name"].replace("#", "-")}.png'))
        im.close()
        
    async def get_profile_path(self, battletag, refresh=False):
        path = os.path.join(self.IMG_CACHE, f'badge-{battletag.replace("#", "-")}.png')
        if not refresh:
            try:
                file_time = os.path.getmtime(path)
                is_expired = ((time.time() - file_time) / 3600 > (self.CACHE_EXPIRE / 60))
                if is_expired:
                    raise FileNotFoundError()
            except FileNotFoundError as e:
                logger.debug(f'failed to found badge for {battletag} on cache')
                return await self.get_profile_path(battletag, refresh=True)
        data = await self.get_stats(battletag, refresh)
        await self.build_profile_image(data)
        return path
