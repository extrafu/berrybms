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

class ConextMPPT(ModbusDevice):

    def __init__(self,
                id,
                connection=None):
        super().__init__(id)
        self.connection = connection

        if self.connection != None:
            self.registers = [
                Register(self, "FGANumber", 0x000A, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "HardwareSerialNumber", 0x002B, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "PVVoltage", 0x004C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "PVCurrent", 0x004E, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "PVPower", 0x0050, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "DCOutputVoltage", 0x0058, ModbusClientMixin.DATATYPE.INT32, 0.001),
                Register(self, "DCOutputCurrent", 0x005A, ModbusClientMixin.DATATYPE.INT32, 0.001),
                Register(self, "DCOutputPower", 0x005C, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "EnergyFromPVThisHour", 0x0070, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyFromPVToday", 0x0074, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "PVInputActiveToday", 0x0076, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "EnergyFromPVThisWeek", 0x0078, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyFromPVThisMonth", 0x007C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyFromPVThisYear", 0x0080, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryThisHour", 0x0088, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryToday", 0x008C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryThisWeek", 0x0090, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryThisMonth", 0x0094, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryThisYear", 0x0098, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "EnergyToBatteryLifetime", 0x009c, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            ]

    def disconnect(self):
        pass

    def publish(self, dict):
        topic_soc = "mppt-%d" % self.id

        if self.registers != None:
            self.values.update(self.dump())
        dict[topic_soc] = self.values

    def formattedOutput(self):
        if self.registers != None:
            self.values.update(self.dump())

        pvPower = self.values.get("PVPower",0)
        dcOutputPower = self.values.get("DCOutputPower",0)
        efficiency = 0

        if dcOutputPower > 0 and pvPower > 0:
            efficiency = dcOutputPower/pvPower

        s = f'== Conext MPPT (id {self.id}) ==\n'
        s += f'PV Input Power:\t\t{pvPower}W - {self.values.get("PVVoltage",0):.2f}v / {self.values.get("PVCurrent",0):.2f}A\n'
        s += f'DC Output Power:\t{dcOutputPower}W - {self.values.get("DCOutputVoltage",0):.2f}v / {self.values.get("DCOutputCurrent",0):.2f}A\n'
        s += f'Efficiency\t\t{efficiency*100:.2f}%\n'
        s += f'PV Energy\t\tHour: {self.values.get("EnergyFromPVThisHour",0):.2f}Wh\tToday: {self.values.get("EnergyFromPVToday",0):.2f}Wh\tWeek: {self.values.get("EnergyFromPVThisWeek",0):.2f}Wh\t Month: {self.values.get("EnergyFromPVThisMonth",0):.2f}Wh'
        return s