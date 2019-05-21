import unittest
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

class TestLaundry(unittest.TestCase):
    def test_availableoftype_with_nofreemachines_uppercase(self):
        testlaundry = laundry.laundry(dataprovider=testprovidernofreemachines(None, None))
        self.assertTrue(len(testlaundry.availableoftype("TUMBLER")) == 0)
        self.assertTrue(len(testlaundry.availableoftype("VASK")) == 0)

    def test_availableoftype_with_nofreemachines_lowercase(self):
        testlaundry = laundry.laundry(dataprovider=testprovidernofreemachines(None, None))
        self.assertTrue(len(testlaundry.availableoftype("tumbler")) == 0)
        self.assertTrue(len(testlaundry.availableoftype("vask")) == 0)

    def test_availableoftype_with_freemachines_uppercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(len(testlaundry.availableoftype("TUMBLER")) == 1)
        self.assertTrue(len(testlaundry.availableoftype("VASK")) == 2)

    def test_availableoftype_with_freemachines_lowercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(len(testlaundry.availableoftype("tumbler")) == 1)
        self.assertTrue(len(testlaundry.availableoftype("vask")) == 2)

    def test_machineexists_lowercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(testlaundry.machineexists("tumbler 1"))
        self.assertTrue(testlaundry.machineexists("tumbler 2"))
        self.assertFalse(testlaundry.machineexists("non_existing_machine"))

    def test_machineexists_uppercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(testlaundry.machineexists("TUMBLER 1"))
        self.assertTrue(testlaundry.machineexists("TUMBLER 2"))
        self.assertFalse(testlaundry.machineexists("NON_EXISTING_MACHINE"))

    def test_ismachineinuse_lowercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(testlaundry.ismachineinuse("tumbler 1"))
        self.assertFalse(testlaundry.ismachineinuse("tumbler 2"))

    def test_ismachineinuse_uppercase(self):
        testlaundry = laundry.laundry(dataprovider=testproviderfreemachines(None, None))
        self.assertTrue(testlaundry.ismachineinuse("TUMBLER 1"))
        self.assertFalse(testlaundry.ismachineinuse("TUMBLER 2"))

    def test_getmachines_withexception(self):
        testlaundry = laundry.laundry(dataprovider=testproviderconnectionerror(None, None))
        testlaundry.getstatustable()

if __name__ == '__main__':
    unittest.main()
