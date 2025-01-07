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

class ConextMPPT(ModbusDevice):

    def __init__(self,
                id,
                connection):
        super().__init__(id)
        self.connection = connection

        self.registers = [
            Register(self.id, "PVVoltage", 0x004C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "PVCurrent", 0x004E, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "PVPower", 0x0050, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "DCOutputVoltage", 0x0058, ModbusClientMixin.DATATYPE.INT32, 0.001),
            Register(self.id, "DCOutputCurrent", 0x005A, ModbusClientMixin.DATATYPE.INT32, 0.001),
            Register(self.id, "DCOutputPower", 0x005C, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "EnergyFromPVThisHour", 0x0070, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyFromPVToday", 0x0074, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "PVInputActiveToday", 0x0076, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "EnergyFromPVThisWeek", 0x0078, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyFromPVThisMonth", 0x007C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyFromPVThisYear", 0x0080, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyToBatteryThisHour", 0x0088, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyToBatteryToday", 0x008C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyToBatteryThisWeek", 0x0090, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "EnergyToBatteryThisMonth", 0x0094, ModbusClientMixin.DATATYPE.UINT32, 0.001),
        ]

    def disconnect(self):
        return None

    def publish(self, dict):
        topic_soc = "mppt-%d" % self.id
        dict[topic_soc] = self.dump()

    def formattedOutput(self):
        dcOutputVoltage = self.getRegister("DCOutputVoltage").value
        dcOutputCurrent = self.getRegister("DCOutputCurrent").value
        dcOutputPower = self.getRegister("DCOutputPower").value
        energyFromPVThisHour = self.getRegister("EnergyFromPVThisHour").value
        energyFromPVToday = self.getRegister("EnergyFromPVToday").value
        energyFromPVThisWeek = self.getRegister("EnergyFromPVThisWeek").value
        energyFromPVThisMonth = self.getRegister("EnergyFromPVThisMonth").value

        s = f"== Conext MPPT (id {self.id}) ==\n"
        s += f"DC Output Power:\t{dcOutputPower}W - {dcOutputVoltage:.2f}v / {dcOutputCurrent:.2f}A\n"
        s += f'PV Energy\t\tHour: {energyFromPVThisHour:.2f}Wh\tToday: {energyFromPVToday:.2f}Wh\tWeek: {energyFromPVThisWeek:.2f}Wh\t Month: {energyFromPVThisMonth:.2f}Wh'
        return s