#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import discord
import configparser
import queue
import json
import logging
import pickle
import asyncio
from laundry import laundry

logging.basicConfig(filename="vask.log", format="[%(asctime)s] %(pathname)s:%(lineno)d %(levelname)s: %(message)s", level=logging.INFO)

logging.info("Bot started")
config = configparser.ConfigParser()
config.read("vask.ini")
token = config["DEFAULT"]["token"]
ip = config["DEFAULT"]["ip"]
url = config["DEFAULT"]["url"]

class job:
    def __init__(self, channel, mention, cmd):
        self.mention = mention
        self.channel = channel
        self.cmd = cmd

    def __str__(self):
        return " ".join([self.mention, str(self.channel), str(self.cmd)])

class VaskeBot(discord.Client):
    def __init__(self, ip, url, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._jobs = queue.Queue()
        self._l = laundry(ip, url)

        try:
            with open("laundry.jobs") as f:
                self._myjobs = pickle.load(f)
        except:
            self._myjobs = []

        #background task
        self.bg_task = self.loop.create_task(self.check_laundry())

    async def check_laundry(self):
        await self.wait_until_ready()
        while not self.is_closed():
            while not self._jobs.empty():
                self._myjobs.append(self._jobs.get())

            logging.info(f"jobs {self._myjobs}")
            if len(self._myjobs) > 0:
                donejobs = []
                for job in self._myjobs:
                    if job.cmd["cmd"] == "mangler":
                        if len(self._l.availableoftype(job.cmd["machinetype"])) > 0:
                            await job.channel.send(f"{job.mention} en maskine af typen {job.cmd['machinetype']} er nu ledig!")
                            donejobs.append(job)
                            break
                    elif job.cmd["cmd"] == "bruger":
                        if not self._l.ismachineinuse(job.cmd["machine"]):
                            await job.channel.send(f"{job.mention} dit tøj i maskine {job.cmd['machine']} er nu færdigt!")
                            donejobs.append(job)
                            break
                for job in donejobs:
                    self._myjobs.remove(job)

                with open("laundry.jobs") as f:
                    pickle.dump(self._myjobs, f)

            await asyncio.sleep(60)

    async def on_message(self, message):
        if any([mention.id == client.user.id for mention in message.mentions]):

            parts = message.content.lower().split(" ")
            cmd = parts[1]
            args = parts[2:]

            if cmd == "status":
                await message.channel.send(f"{message.author.mention}```\n{self._l.getstatustable()}```")
            elif cmd == "bruger" and len(args) > 0:
                name = " ".join(args).lower()
                if not self._l.machineexists(name):
                    await message.channel.send(f"{message.author.mention} maskinen findes ikke")
                    return

                if not self._l.ismachineinuse(name):
                    await message.channel.send(f"{message.author.mention} maskinen er fri lige nu. Så er dit vasketøj færdigt?")
                    return

                await message.channel.send(f"{message.author.mention} Jeg holder øje med dit vasketøj")
                self._jobs.put(
                        job(
                            message.channel,
                            message.author.mention,
                            { "cmd": cmd, "machine": name }
                            )
                        )
            elif cmd == "mangler" and len(args) > 0:
                available = self._l.availableoftype(args[0])
                if len(available) > 0:
                    await message.channel.send(f"{message.author.mention} Der er en ledig maskine af den type lige nu!")
                    return

                await message.channel.send(f"{message.author.mention} Du får besked, når der er en fri maskine")
                self._jobs.put(
                        job(
                            message.channel,
                            message.author.mention,
                            { "cmd": cmd, "machinetype": args[0] }
                            )
                        )
            elif cmd == "help":
                await message.channel.send(
                """```
Jeg tager i mod følgende kommandoer:
status - få status over alle maskiner
bruger [maskine] - giver en notifikation, når maskinen er færdig
mangler [type] - giver en notifikation, når maskintype er ledig
help - denne besked
                ```""")
client = VaskeBot(ip, url)
client.run(token)
