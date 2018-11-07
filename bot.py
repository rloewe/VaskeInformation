import discord
import asyncio
import configparser
import queue
import threading
import requests
import time
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

    def tostring(self):
        return u" ".join([self.name, self.price, self.status, self.timeleft, self.started])

    def isavailable(self):
        return self.status.lower() == "fri"

    def _convert_nbsp(self, string):
        return string.replace("\xa0", " ")

class laundry:
    def __init__(self, url):
        self.url = url
        self.availablemachines = self.getmachines()

    def getmachines(self):
        req = requests.get(self.url)
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
        else:
            print("something went wrong")
            return []

    def machineexists(self, name):
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
        table = PrettyTable(["navn", "pris", "status", "tid tilbage", "startet"])
        [table.add_row([x.name, x.price, x.status, x.timeleft, x.started]) for x in machines]
        return table.get_string()

    def availableoftype(self, machinetype):
        machines = self.getmachines()
        available = []
        for machine in machines:
            if machine.isavailable:
                available.append(machine)
        return machines

class job:
    def __init__(self, mention, cmd):
        self.mention = mention
        self.cmd = cmd

class notifier(threading.Thread):
    def run(self):
        myjobs = []
        while True:
            time.sleep(60)
            while not jobs.empty():
                myjobs.append(jobs.get())
            print(client)
            machines = l.getmachines()
            for job in myjobs:
                if job.cmd.cmd == "mangler":
                    for machine in machines:
                        if machine.gettype() == job.cmd.machinetype:
                            print("lul")
                            break
                elif job.cmd.cmd == "bruger":
                    for machine in machines:
                        if machine.name == job.cmd.machine:
                            print("lul")
                            break


client = discord.Client()
config = configparser.ConfigParser()
config.read("vask.ini")
token = config["DEFAULT"]["token"]
url = config["DEFAULT"]["url"]
jobs = queue.Queue()
l = laundry(url)

@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("")

@client.event
async def on_message(message):
    if any([mention.id == client.user.id for mention in message.mentions]):

        parts = message.content.lower().split(" ")
        cmd = parts[1]
        args = parts[2:]

        if cmd == "status":
            machines = l.getmachines()
            await client.send_message(message.channel, message.author.mention + "```\n" + l.getstatustable()  +  "```")
        elif cmd == "bruger" and len(args) > 0:
            name = " ".join(args).lower()
            if not l.machineexists(name):
                await client.send_message(message.channel, message.author.mention + " maskinen findes ikke")
                return

            if not l.ismachineinuse(name):
                await client.send_message(message.channel, message.author.mention + " maskinen er fri lige nu. Så er dit vasketøj færdigt?")
                return

            await client.send_message(message.channel, message.author.mention + " Jeg holder øje med dit vasketøj")
            jobs.put(job(mention, { cmd: cmd, machine: name }))
        elif cmd == "mangler" and len(args) > 0:
            available = l.availableoftype(args[0])
            if len(available) > 0:
                await client.send_message(message.channel, message.author.mention + "Der er en ledig maskine af den type lige nu!")

            await client.send_message(message.channel, message.author.mention + " Du får besked, når der er en fri maskine")
            jobs.put(job(mention, { cmd: cmd, machinetype: args[0] }))
        elif cmd == "help":
            await client.send_message(message.channel, """```
Jeg tager i mod følgende kommandoer:
status - få status over alle maskiner
bruger [maskine] - giver en notifikation, når maskinen er færdig
mangler [type] - giver en notifikation, når maskintype er ledig
help - denne besked
            ```""")

notifier().start()
client.run(token)
