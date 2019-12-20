import laundry
import requests

class testprovidernofreemachines(laundry.dataprovider):
    def __init__(self, ip, uri):
        return

    def getmachines(self):
        return [
                laundry.machine("VASK 1", "1", "optaget", "15", "00:00"),
                laundry.machine("VASK 2", "1", "optaget", "15", "00:00"),
                laundry.machine("TUMBLER 1", "1", "optaget", "15", "00:00"),
                laundry.machine("TUMBLER 2", "1", "optaget", "15", "00:00"),
                ]

class testproviderfreemachines(laundry.dataprovider):
    def __init__(self, ip, uri):
        return

    def getmachines(self):
        return [
                laundry.machine("VASK 1", "1", "fri", "15", "00:00"),
                laundry.machine("VASK 2", "1", "fri", "15", "00:00"),
                laundry.machine("TUMBLER 1", "1", "optaget", "15", "00:00"),
                laundry.machine("TUMBLER 2", "1", "fri", "15", "00:00"),
                ]

class testproviderconnectionerror(laundry.dataprovider):
    def __init__(self, ip, uri):
        return

    def getmachines(self):
        raise requests.ConnectionError

def test_availableoftype_with_nofreemachines_uppercase():
    testlaundry = laundry.laundry(dataprovider=testprovidernofreemachines(None, None))
    assert len(testlaundry.availableoftype("TUMBLER")) == 0
    assert len(testlaundry.availableoftype("VASK")) == 0

def test_availableoftype_with_nofreemachines_lowercase():
    testlaundry = laundry.laundry(dataprovider=testprovidernofreemachines(None, None))
    assert len(testlaundry.availableoftype("tumbler")) == 0
    assert len(testlaundry.availableoftype("vask")) == 0

def test_availableoftype_with_freemachines_uppercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert len(testlaundry.availableoftype("TUMBLER")) == 1
    assert len(testlaundry.availableoftype("VASK")) == 2

def test_availableoftype_with_freemachines_lowercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert len(testlaundry.availableoftype("tumbler")) == 1
    assert len(testlaundry.availableoftype("vask")) == 2

def test_machineexists_lowercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert testlaundry.machineexists("tumbler 1")
    assert testlaundry.machineexists("tumbler 2")
    assert not testlaundry.machineexists("non_existing_machine")

def test_machineexists_uppercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert testlaundry.machineexists("TUMBLER 1")
    assert testlaundry.machineexists("TUMBLER 2")
    assert  not testlaundry.machineexists("NON_EXISTING_MACHINE")

def test_ismachineinuse_lowercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert testlaundry.ismachineinuse("tumbler 1")
    assert not testlaundry.ismachineinuse("tumbler 2")

def test_ismachineinuse_uppercase():
    testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
    assert testlaundry.ismachineinuse("TUMBLER 1")
    assert not testlaundry.ismachineinuse("TUMBLER 2")

def test_getmachines_withexception():
    testlaundry = laundry.laundry(dataprovider=testproviderconnectionerror(None, None))
    testlaundry.getstatustable()
