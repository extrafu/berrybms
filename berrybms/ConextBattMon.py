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
from pymodbus.client.mixin import ModbusClientMixin # type: ignore

import json

from ModbusDevice import ModbusDevice
from Register import Register

class ConextBattMon(ModbusDevice):

    def __init__(self,
                id,
                connection=None):
        super().__init__(id)
        self.connection = connection

        self.values = {}

        if self.connection != None:
            self.registers = [
                Register(self, "FGANumber", 0x000A, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "HardwareSerialNumber", 0x002B, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "BatteryVoltage", 0x0046, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatteryCapacity", 0x0092, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "BatteryCapacityRemaining", 0x0058, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "BatteryCapacityRemoved", 0x005A, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "BatteryCurrent", 0x0048, ModbusClientMixin.DATATYPE.INT32, 0.001),
                Register(self, "BatteryMidpoint1Voltage", 0x0052, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatteryMidpoint2Voltage", 0x0054, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatteryMidpoint3Voltage", 0x0056, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatterySOC", 0x004C, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "BatteryStateOfHealth", 0x004E, DataType.UINT32)       # useless, returns 0
            ]

    def disconnect(self):
        pass

    def publish(self, dict):
        topic_soc = "battmon-%d" % self.id

        if self.registers != None:
            self.values.update(self.dump())
        dict[topic_soc] = self.values
    
    def formattedOutput(self):
        if self.registers != None:
            self.values.update(self.dump())
        
        s = f'== Conext BattMon (id {self.id}) ==\n'
        s += f'Capacity:\t\t{self.values.get("BatteryCapacityRemaining",0)}Ah of {self.values.get("BatteryCapacity",0)}Ah ({self.values.get("BatteryCapacityRemoved",0)}Ah removed)\n'
        s += f'Active Power:\t\t{self.values.get("BatteryVoltage",0):.2f}v / {self.values.get("BatteryCurrent",0):.2f}A\n'
        s += f'SOC:\t\t\t{self.values.get("BatterySOC",0)}%'

        return s