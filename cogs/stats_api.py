import json
import logging
import os

import aiohttp
from discord.ext import commands, tasks

GIST_FILENAME = "stats.json"


class StatsAPI(commands.Cog):
    """Publishes public bot stats (server and user counts) to a GitHub Gist for the website.

    Needs two .env values:
      GITHUB_TOKEN    - a GitHub token with only the "gist" scope
      STATS_GIST_ID   - the ID of a gist containing a file named stats.json
    If either is missing, the cog does nothing.
    """

    def __init__(self, bot):
        self.bot = bot
        self.token = os.getenv("GITHUB_TOKEN")
        self.gist_id = os.getenv("STATS_GIST_ID")
        self.last_published = None

    async def cog_load(self):
        if self.token and self.gist_id:
            self.publish_stats.start()
        else:
            logging.info("Stats publishing disabled: GITHUB_TOKEN or STATS_GIST_ID not set")

    async def cog_unload(self):
        self.publish_stats.cancel()

    def current_stats(self):
        guilds = self.bot.guilds
        return {
            "servers": len(guilds),
            # Members are counted once per server, so a user in two servers counts twice.
            "users": sum(g.member_count or 0 for g in guilds),
        }

    @tasks.loop(minutes=10)
    async def publish_stats(self):
        stats = self.current_stats()
        if stats == self.last_published:
            return  # Nothing changed; don't create a new gist revision.

        url = f"https://api.github.com/gists/{self.gist_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        body = {"files": {GIST_FILENAME: {"content": json.dumps(stats)}}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=body) as res:
                    if res.status == 200:
                        self.last_published = stats
                    else:
                        logging.error(f"Stats gist update failed: {res.status} {await res.text()}")
        except aiohttp.ClientError as e:
            logging.error(f"Stats gist update failed: {e}")

    @publish_stats.before_loop
    async def before_publish(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StatsAPI(bot))
