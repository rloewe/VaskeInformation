import requests
import os
import time
from prettytable import PrettyTable
from lxml import html
from abc import ABC, abstractmethod
import pickle
import logging

class machine:
    def __init__(self, name, price, status, timeleft, started):
        self.name     = self._convert_nbsp(name.strip())
        self.price    = self._convert_nbsp(price.strip())
        self.status   = self._convert_nbsp(status.strip())
        self.timeleft = self._convert_nbsp(timeleft.strip())
        self.started  = self._convert_nbsp(started.strip())

    def gettype(self):
        return self.name.split(" ")[0].lower()

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

class dataprovider(ABC):
    @abstractmethod
    def __init__(self, ip, uri):
        pass

    @abstractmethod
    def getmachines(self):
        pass

class laundrydataprovider(dataprovider):
    def __init__(self, ip, uri):
        self._url = f"http://{ip}{uri}"

        if os.path.isfile(".session"):
            with open(".session", "rb") as f:
                self._session = pickle.load(f)
        else:
            self._session = requests.Session()

        # Make sure system is up and running
        self._session.get(f"http://{ip}")

        self.dumpsession()

    def getmachines(self):
        req = self._session.get(self._url)
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
            # TODO: fix busy webserver
            # Session cookies have been added as a possible fix for this
            logging.warning("Server says it is busy")
        else:
            logging.warning(f"Something went wrong. Status: {req.status_code}, Text: {req.text}")
            return []

    def dumpsession(self):
        with open(".session", "wb") as f:
            pickle.dump(self._session, f)


class laundry:
    def __init__(self, ip = None, url = None, dataprovider = None):
        if dataprovider == None:
            self._dataprovider = laundrydataprovider(ip, url)
        else:
            self._dataprovider = dataprovider

        self.availablemachines = []
        self._lastcacheupdate = -1
        self._dataavailable = False
        self._errortext = "Der er i øjeblikket ingen tilgængelige data. Vaskeriet må være nede"

    def machineexists(self, name):
        self._fixlocalcache()

        if self._dataavailable:
            for machine in self.availablemachines:
                if machine.name.lower() == name.lower():
                    return True
        return False

    def ismachineinuse(self, name):
        self._fixlocalcache()
        if self._dataavailable:
            for machine in self.availablemachines:
                if machine.name.lower() == name.lower():
                    return not machine.isavailable()
        else:
            return False

    def getstatustable(self):
        self._fixlocalcache()
        if self._dataavailable:
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
                ]) for x in self.availablemachines]
            return table.get_string()
        else:
            return self._errortext

    def availableoftype(self, machinetype):
        self._fixlocalcache()

        available = []
        for machine in self.availablemachines:
            if machine.isavailable() and machine.gettype() == machinetype.lower():
                available.append(machine)
        return available

    def _fixlocalcache(self):
        current_time = time.time()
        if current_time-self._lastcacheupdate > 40:
            try:
                self.availablemachines = self._dataprovider.getmachines()
                self._dataavailable = True
            except requests.ConnectionError:
                self._dataavailable = False
