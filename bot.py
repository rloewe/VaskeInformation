#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import discord
import configparser
import queue
import json
import zlib
import logging
import pickle
from laundry import laundry

logging.basicConfig(filename="vask.log", format="[%(asctime)s] %(levelname)s: %(message)s", level=logging.INFO)

logging.info("Bot started")
client = discord.Client()
config = configparser.ConfigParser()
config.read("vask.ini")
token = config["DEFAULT"]["token"]
ip = config["DEFAULT"]["ip"]
url = config["DEFAULT"]["url"]
jobs = queue.Queue()
l = laundry(ip, url)
_zlib = zlib.decompressobj()

try:
    with open("laundry.jobs") as f:
        myjobs = pickle.load(f)
except:
    myjobs = []

class job:
    def __init__(self, channel, mention, cmd):
        self.mention = mention
        self.channel = channel
        self.cmd = cmd

    def __str__(self):
        return " ".join([self.mention, str(self.channel), str(self.cmd)])

@client.event
async def on_ready():
    logging.info("Logged in as %s, %s", client.user.name, client.user.id)

@client.event
async def on_socket_raw_receive(msg):
    decoded = _zlib.decompress(msg).decode('utf-8')
    if isinstance(decoded, str):
        event = json.loads(decoded)
        # React to heartbeat event
        if isinstance(event, dict) and event["op"] == 11:
            while not jobs.empty():
                myjobs.append(jobs.get())

            logging.info(f"jobs {myjobs}")
            if len(myjobs) > 0:
                donejobs = []
                for job in myjobs:
                    if job.cmd["cmd"] == "mangler":
                        if len(l.availableoftype(job.cmd["machinetype"])) > 0:
                            await job.channel.send(f"{job.mention} en maskine af typen {job.cmd['machinetype']} er nu ledig!")
                            donejobs.append(job)
                            break
                    elif job.cmd["cmd"] == "bruger":
                        if not l.ismachineinuse(job.cmd["machine"]):
                            await job.channel.send(f"{job.mention} dit tøj i maskine {job.cmd['machine']} er nu færdigt!")
                            donejobs.append(job)
                            break
                for job in donejobs:
                    myjobs.remove(job)

                with open("laundry.jobs") as f:
                    pickle.dump(myjobs, f)

@client.event
async def on_message(message):
    if any([mention.id == client.user.id for mention in message.mentions]):

        parts = message.content.lower().split(" ")
        cmd = parts[1]
        args = parts[2:]

        if cmd == "status":
            await message.channel.send(f"{message.author.mention}```\n{l.getstatustable()}```")
        elif cmd == "bruger" and len(args) > 0:
            name = " ".join(args).lower()
            if not l.machineexists(name):
                await message.channel.send(f"{message.author.mention} maskinen findes ikke")
                return

            if not l.ismachineinuse(name):
                await message.channel.send(f"{message.author.mention} maskinen er fri lige nu. Så er dit vasketøj færdigt?")
                return

            await message.channel.send(f"{message.author.mention} Jeg holder øje med dit vasketøj")
            jobs.put(
                    job(
                        message.channel,
                        message.author.mention,
                        { "cmd": cmd, "machine": name }
                        )
                    )
        elif cmd == "mangler" and len(args) > 0:
            available = l.availableoftype(args[0])
            if len(available) > 0:
                await message.channel.send(f"{message.author.mention} Der er en ledig maskine af den type lige nu!")
                return

            await message.channel.send(f"{message.author.mention} Du får besked, når der er en fri maskine")
            jobs.put(
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

client.run(token)
