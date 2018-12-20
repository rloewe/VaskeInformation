#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import discord
import asyncio
import configparser
import queue
import threading
import requests
import time
import pickle
import json
import os
from prettytable import PrettyTable
from lxml import html

class machine:
    def __init__(self, name, price, status, timeleft, started):
        self.name     = self._convert_nbsp(name.strip())
        self.price    = self._convert_nbsp(price.strip())
        self.status   = self._convert_nbsp(status.strip())
        self.timeleft = self._convert_nbsp(timeleft.strip())
        self.started  = self._convert_nbsp(started.strip())

    def gettype(self):
        return self.name.split(" ")[0]

    def isavailable(self):
        return self.status.lower() == "fri"

    def _convert_nbsp(self, string):
        return string.replace("\xa0", " ")

    def __str__(self):
        return u" ".join([
            self.name,
            self.price,
            self.status,
            self.timeleft,
            self.started
            ])

class laundry:
    def __init__(self, ip, url):
        self.url = "http://" + ip + url

        if os.path.isfile(".session"):
            with open(".session", "rb") as f:
                self._session = pickle.load(f)
        else:
            self._session = requests.Session()

        # Make sure system is up and running
        self._session.get("http://" + ip)

        self.dumpsession()

        self.availablemachines = []


    def getmachines(self):
        req = self._session.get(self.url)
        self.dumpsession()
        machines = []

        if req.status_code == 200:
            elements = html.fromstring(req.text).xpath("//tr")
            for element in elements[3:]:
                subelements = element.xpath("./td")
                if len(subelements) > 4:
                    machines.append(
                            machine(
                                subelements[0].text_content(),
                                subelements[1].text_content(),
                                subelements[2].text_content(),
                                subelements[3].text_content(),
                                subelements[4].text_content(),
                                )
                            )
            return machines
        elif req.status_code == 403:
            #TODO: fix busy webserver
            # Session cookies have been added as a possible fix for this
            print("Server says it is busy")
        else:
            print(req.status_code)
            print(req.text)
            print("something went wrong")
            return []

    def machineexists(self, name):
        if len(self.availablemachines) == 0:
            self.fixlocalcache()

        for machine in self.availablemachines:
            if machine.name.lower() == name:
                return True
        return False

    def ismachineinuse(self, name):
        machines = self.getmachines()
        for machine in machines:
            if machine.name.lower() == name:
                return not machine.isavailable()


    def getstatustable(self):
        machines = self.getmachines()
        table = PrettyTable([
            "navn",
            "pris",
            "status",
            "tid tilbage",
            "startet"])
        [table.add_row([
            x.name,
            x.price,
            x.status,
            x.timeleft,
            x.started
            ]) for x in machines]
        return table.get_string()

    def availableoftype(self, machinetype):
        machines = self.getmachines()
        available = []
        for machine in machines:
            if machine.isavailable:
                available.append(machine)
        return machines

    def fixlocalcache(self):
        self.availablemachines = self.getmachines()

    def dumpsession(self):
        with open(".session", "wb") as f:
            pickle.dump(self._session, f)

class job:
    def __init__(self, channel, mention, cmd):
        self.mention = mention
        self.channel = channel
        self.cmd = cmd

    def __str__(self):
        return " ".join([self.mention, str(self.channel), str(self.cmd)])

client = discord.Client()
config = configparser.ConfigParser()
config.read("vask.ini")
token = config["DEFAULT"]["token"]
ip = config["DEFAULT"]["ip"]
url = config["DEFAULT"]["url"]
jobs = queue.Queue()
l = laundry(ip, url)
myjobs = []

@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("")

@client.event
async def on_socket_raw_receive(msg):
    if isinstance(msg, str):
        event = json.loads(msg)
        # React to heartbeet event
        if isinstance(event, dict) and event["op"] == 11:
            while not jobs.empty():
                myjobs.append(jobs.get())

            if len(myjobs) > 0:
                machines = l.getmachines()
                donejobs = []
                for job in myjobs:
                    if job.cmd["cmd"] == "mangler":
                        for machine in machines:
                            if machine.gettype().lower() == job.cmd["machinetype"].lower() and machine.isavailable():
                                await client.send_message(
                                        job.channel,
                                        job.mention
                                            + " en maskine af typen "
                                            + job.cmd["machinetype"]
                                            + " er nu ledig!"
                                        )
                                donejobs.append(job)
                                break
                    elif job.cmd["cmd"] == "bruger":
                        for machine in machines:
                            if machine.name.lower() == job.cmd["machine"].lower() and machine.isavailable():
                                await client.send_message(
                                        job.channel,
                                        job.mention
                                            + u" dit tøj i maskine "
                                            + job.cmd["machine"]
                                            + u" er nu færdigt!"
                                        )
                                donejobs.append(job)
                                break
                for job in donejobs:
                    myjobs.remove(job)

@client.event
async def on_message(message):
    if any([mention.id == client.user.id for mention in message.mentions]):

        parts = message.content.lower().split(" ")
        cmd = parts[1]
        args = parts[2:]

        if cmd == "status":
            await client.send_message(
                    message.channel,
                    message.author.mention
                        + "```\n"
                        + l.getstatustable()
                        +  "```"
                    )
        elif cmd == "bruger" and len(args) > 0:
            name = " ".join(args).lower()
            if not l.machineexists(name):
                await client.send_message(
                        message.channel,
                        message.author.mention + " maskinen findes ikke"
                        )
                return

            if not l.ismachineinuse(name):
                await client.send_message(
                        message.channel,
                        message.author.mention
                            + " maskinen er fri lige nu. Så er dit vasketøj færdigt?"
                        )
                return

            await client.send_message(
                    message.channel,
                    message.author.mention + " Jeg holder øje med dit vasketøj"
                    )
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
                await client.send_message(
                        message.channel,
                        message.author.mention
                            + "Der er en ledig maskine af den type lige nu!"
                        )
                return

            await client.send_message(
                    message.channel,
                    message.author.mention
                        + " Du får besked, når der er en fri maskine"
                    )
            jobs.put(
                    job(
                        message.channel,
                        message.author.mention,
                        { "cmd": cmd, "machinetype": args[0] }
                        )
                    )
        elif cmd == "help":
            await client.send_message(
            message.channel,
            """```
Jeg tager i mod følgende kommandoer:
status - få status over alle maskiner
bruger [maskine] - giver en notifikation, når maskinen er færdig
mangler [type] - giver en notifikation, når maskintype er ledig
help - denne besked
            ```""")

client.run(token)
