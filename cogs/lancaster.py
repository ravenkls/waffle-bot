import datetime
import json
import logging
import os
import re
from contextlib import asynccontextmanager

import aiohttp
import discord
import xmltodict
from async_lru import alru_cache
from bs4 import BeautifulSoup
from dateutil import parser
from discord.ext import commands, tasks
from dateutil.parser import isoparse

from .base import BaseCog
from .utils.db.database import DBFilter
from .utils.db.fields import *


class Lancaster(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.emoji = "🌹"
        self.session = None
        self.logger = logging.getLogger(__name__)

    async def setup(self):
        self.moodle_posts = await self.bot.database.new_table(
            "demographics_roles",
            (BigInteger("guild_id"), Varchar("post_id", 1000)),
        )
        self.check_for_announcements_task.start()

    @alru_cache(maxsize=10)
    async def login_to_portal(self, username, password):
        session = aiohttp.ClientSession()

        async with session.get("https://weblogin.lancs.ac.uk/login/") as login_page:
            html = await login_page.text()
            soup = BeautifulSoup(html, "lxml")
            form = soup.select_one("form#loginbox")
            data = {f["name"]: f["value"] for f in form.find_all("input")}
            data["username"] = username

        async with session.post(
            "https://weblogin.lancs.ac.uk/login/", data=data
        ) as pw_page:
            html = await pw_page.text()
            soup = BeautifulSoup(html, "lxml")
            form = soup.select_one("form#loginbox")
            data = {f["name"]: f["value"] for f in form.find_all("input")}
            data["password"] = password

        resp = await session.post("https://weblogin.lancs.ac.uk/login/", data=data)
        html = await resp.text()
        if "You are logged into" in html:
            return session

    async def get_news(self):
        with open(os.path.join("data", "forums.json")) as forums_file:
            forum_data = json.load(forums_file)

        announcements = []
        session = await self.login_to_portal(*self.bot.login_data)
        for forum in forum_data:
            resp = await session.get(
                f"https://modules.lancaster.ac.uk/mod/forum/view.php?id={forum['id']}"
            )
            content = await resp.text()
            soup = BeautifulSoup(content, "lxml")
            rows = soup.select_one("tbody").find_all("tr")
            for row in rows:
                icon, group, author, *other = row.find_all("td")
                if not group.text.strip():
                    title = row.select_one("th").text.strip()
                    avatar = author.select_one("img")["src"]
                    _id = re.findall(
                        r"[?&]d=(\d+)$", row.select_one("th a")["href"].strip()
                    )[0]

                    if title.endswith("Locked"):
                        title = title[:-6]

                    author_name, date = author.select_one(".author-info").find_all(
                        "div"
                    )

                    announcement = {
                        "title": title.strip(),
                        "author": author_name.text.strip(),
                        "date": datetime.datetime.strptime(
                            date.text.strip(), "%d %b %Y"
                        ),
                        "url": "https://modules.lancaster.ac.uk/mod/forum/discuss.php?d="
                        + str(_id),
                        "avatar": avatar,
                        "id": _id,
                    }
                    announcements.append(announcement)

        latest = sorted(announcements, key=lambda x: x["date"], reverse=True)
        return latest

    @alru_cache(maxsize=100)
    async def get_extra_details(self, _id):
        session = await self.login_to_portal(*self.bot.login_data)
        resp = await session.get(
            f"https://modules.lancaster.ac.uk/mod/forum/discuss.php?d={_id}"
        )
        content = await resp.text()
        soup = BeautifulSoup(content, "lxml")
        return {
            "description": "\n\n".join(
                [
                    x.text
                    for x in soup.select_one(".post-content-container").find_all("p")
                ]
            )[:1000],
            "date": isoparse(soup.select_one("time")["datetime"]),
        }

    async def news_embed(self, data):
        details = await self.get_extra_details(data["id"])

        embed = discord.Embed(
            title=data["title"],
            url=data["url"],
            colour=0xFF0000,
            timestamp=details["date"],
            description=details["description"],
        )
        embed.set_author(name=data["author"], icon_url=data["avatar"])
        return embed

    @commands.command()
    async def cleardb(self, ctx):
        await self.moodle_posts.delete_records()
        await ctx.send("done")

    @commands.is_owner()
    @commands.command()
    async def announcementchannel(self, ctx, channel: discord.TextChannel = None):
        if channel:
            channel_id = str(channel.id)
            await self.bot.database.set_setting(
                ctx.guild, "announcement_channel", channel_id
            )
            await ctx.send(f"{channel.mention} is now the announcement channel")
            await self.check_for_announcements()
        else:
            await ctx.send("Announcement channel reset")

    async def get_announcement_channel(self, guild):
        channel_id = await self.bot.database.get_setting(guild, "announcement_channel")
        if channel_id:
            return guild.get_channel(int(channel_id))

    async def check_for_announcements(self):
        self.logger.info("Checking for new announcements.")
        announcements = await self.get_news()
        n = 0
        for news in reversed(announcements[:5]):
            for guild in self.bot.guilds:
                exists = await self.moodle_posts.filter(
                    where=DBFilter(guild_id=guild.id, post_id=news["id"])
                )
                if not exists:
                    channel = await self.get_announcement_channel(guild)
                    if channel:
                        embed = await self.news_embed(news)
                        await channel.send(embed=embed)
                        await self.moodle_posts.new_record(
                            guild_id=guild.id, post_id=news["id"]
                        )
                        n += 1
        if n:
            self.logger.info(f"Found {n} new announcements.")
        else:
            self.logger.info("No new announcements found.")

    @tasks.loop(minutes=10)
    async def check_for_announcements_task(self):
        await self.check_for_announcements()


def setup(bot):
    bot.add_cog(Lancaster(bot))
