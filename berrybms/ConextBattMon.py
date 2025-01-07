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
from pymodbus.client.mixin import ModbusClientMixin

import json

from ModbusDevice import ModbusDevice
from Register import Register

class ConextBattMon(ModbusDevice):

    def __init__(self,
                id,
                connection):
        super().__init__(id)
        self.connection = connection

        self.registers = [
            Register(self.id, "BatteryVoltage", 0x0046, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatteryCapacity", 0x0092, ModbusClientMixin.DATATYPE.UINT16),
            Register(self.id, "BatteryCapacityRemaining", 0x0058, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "BatteryCapacityRemoved", 0x005A, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "BatteryCurrent", 0x0048, ModbusClientMixin.DATATYPE.INT32, 0.001),
            Register(self.id, "BatteryMidpoint1Voltage", 0x0052, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatteryMidpoint2Voltage", 0x0054, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatteryMidpoint3Voltage", 0x0056, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatterySOC", 0x004C, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "BatteryStateOfHealth", 0x004E, DataType.UINT32)       # useless, returns 0
        ]

    def disconnect(self):
        return None

    def publish(self, dict):
        topic_soc = "battmon-%d" % self.id
        dict[topic_soc] = self.dump()
    
    def formattedOutput(self):
        voltage = self.getRegister("BatteryVoltage").value
        capacity = self.getRegister("BatteryCapacity").value
        capacityRemaining = self.getRegister("BatteryCapacityRemaining").value
        capacityRemoved = self.getRegister("BatteryCapacityRemoved").value
        current = self.getRegister("BatteryCurrent").value
        soc = self.getRegister("BatterySOC").value
        
        s = f"== Conext BattMon (id {self.id}) ==\n"
        s += f"Capacity:\t\t{capacityRemaining}Ah of {capacity}Ah ({capacityRemoved}Ah removed)\n"
        s += f"Active Power:\t\t{voltage:.2f}v / {current}A\n"
        s += f'SOC:\t\t\t{soc}%'

        return s