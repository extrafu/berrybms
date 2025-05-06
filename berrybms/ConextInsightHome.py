#
# Copyright (C) 2025 Extrafu <extrafu@gmail.com>
#
# This file is part of BerryBMS.
#
# BerryBMS is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any
# later version.
#
import pymodbus.client as ModbusClient # type: ignore
from pymodbus.client.mixin import ModbusClientMixin # type: ignore

from ModbusDevice import ModbusDevice
from ConextAGS import ConextAGS
from ConextBattMon import ConextBattMon
from ConextMPPT import ConextMPPT
from ConextSCP import ConextSCP # type: ignore
from ConextXW import ConextXW
from Register import Register

class ConextInsightHome(ModbusDevice):

    # See Modbus Map: Conext ModbusConverter/ComBox Device documentation
    # for Product ID <> Description mapping on all Conext products
    ConextProductMap = {
        "865-1032":     ConextMPPT,
        "865-1050":     ConextSCP,
        "865-1050-01":  ConextSCP,
        "865-1060-01":  ConextAGS,      # Missing -01 in documentation
        "865-1080-01":  ConextBattMon,  # Not documented
        "865-6848-01":  ConextXW
    }

    def __init__(self,
                 host=None,
                 port=None,
                 ids=None,
                 serial_number_hack=None):
        super().__init__(id)
        self.host = host
        self.port = port
        self.ids = ids
        self.serial_number_hack = serial_number_hack
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
            device = ModbusDevice(i)
            # We don't use the DeviceName as it can be changed in the InsightHome/Combox
            reg = Register(device, "FGANumber", 0x000A, ModbusClientMixin.DATATYPE.STRING, None, 10)
            value = reg.getValue(self.connection)

            if value == None:
                #print("No device for id %d", i)
                continue

            # We got something!
            clazz = ConextInsightHome.ConextProductMap.get(str(value), None)

            if clazz == None:
                print(f"Unknown Conext device {str(value)}")
                continue

            # All is good, let's fetch the serial number that we will use as the
            # unique identifier for all devices. We fist check if we need use the
            # hack, which is useful for XW+6848 returning a modbus exception when
            # trying to fetch the HardwareSerialNumber :/
            if self.serial_number_hack != None and self.serial_number_hack.get(i, None) != None:
                value = self.serial_number_hack[i]
            else:
                reg = Register(device, "HardwareSerialNumber", 0x002B, ModbusClientMixin.DATATYPE.STRING, None, 10)
                value = reg.getValue(self.connection)

                if value == None:
                    print(f"No hardware serial number for id {i} of type {clazz}")
                    continue

            self.devices.append(clazz(i, value, self.connection))

        return self.devices
    


