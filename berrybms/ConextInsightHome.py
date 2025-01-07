import pymodbus.client as ModbusClient
from pymodbus.client.mixin import ModbusClientMixin

from ModbusDevice import ModbusDevice
from ConextAGS import ConextAGS
from ConextBattMon import ConextBattMon
from ConextMPPT import ConextMPPT
from ConextXW import ConextXW
from Register import Register

class ConextInsightHome(ModbusDevice):

    def __init__(self,
                 host,
                 port,
                 ids):
        super().__init__(id)
        self.host = host
        self.port = port
        self.ids = ids
        self.devices = []
    
    def connect(self):
        if self.connection == None:
            self.connection = ModbusClient.ModbusTcpClient(self.host, port=self.port, timeout=10)
            if self.connection.connect():
                print("Connected over modbus/TCP!")
            else:
                print("Cannot connect to modbus/TCP")
                self.connection = None

        return self.connection

    def allDevices(self):
        if self.ids == None:
            self.ids = range(1,247)

        for i in self.ids:
            reg = Register(i, "DeviceName", 0x0000, ModbusClientMixin.DATATYPE.STRING, None, 8)
            value = reg.getValue(self.connection)
            if value == None:
                #print("No device for id %d", i)
                continue

            # We got something! Here are some valid prefixes
            # cb-
            # XW6848
            # XW AGS
            # XW SCP
            # XW MPPT
            # BattMon
            #print("Conext device %d: %s" % (i, value))
            if str(value).startswith("BattMon"):
                self.devices.append(ConextBattMon(i, self.connection))

            if str(value).startswith("XW6848"):
                self.devices.append(ConextXW(i, self.connection))

            if str(value).startswith("XW AGS"):
                self.devices.append(ConextAGS(i, self.connection))

            if str(value).startswith("XW MPPT"):
                self.devices.append(ConextMPPT(i, self.connection))

        return self.devices
    


