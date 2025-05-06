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
import json

from ModbusDevice import ModbusDevice
from Register import Register

class ConextXW(ModbusDevice):

    def __init__(self,
                id,
                serial_number=None,
                connection=None):
        super().__init__(id, serial_number)
        self.connection = connection

        if self.connection != None:
            self.registers = [
                Register(self, "EnergyFromBatteryThisHour", 0x00D0, ModbusClientMixin.DATATYPE.UINT32, 0.001), # looks like what goes INTO the battery from AC1/AC2
                Register(self, "EnergyFromBatteryToday", 0x00D4, ModbusClientMixin.DATATYPE.UINT32, 0.001),    # looks like what goes INTO the battery from AC1/AC2
                Register(self, "BatteryDischargeActiveToday", 0x00D6, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "EnergyFromBatteryThisWeek", 0x00D8, ModbusClientMixin.DATATYPE.UINT32, 0.001), # looks like what goes INTO the battery from AC1/AC2
                Register(self, "EnergyFromBatteryThisMonth", 0x00DC, ModbusClientMixin.DATATYPE.UINT32, 0.001),# looks like what goes INTO the battery from AC1/AC2 
                Register(self, "EnergyToBatteryThisHour", 0x00E8, ModbusClientMixin.DATATYPE.UINT32, 0.001),   # looks like what we PULL from the battery
                Register(self, "EnergyToBatteryToday", 0x00EC, ModbusClientMixin.DATATYPE.UINT32, 0.001),      # looks like what we PULL from the battery
                Register(self, "BatteryChargeActiveToday", 0x00EE, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "EnergyToBatteryThisWeek", 0x00F0, ModbusClientMixin.DATATYPE.UINT32, 0.001),   # looks like what we PULL from the battery
                Register(self, "EnergyToBatteryThisMonth", 0x00F4, ModbusClientMixin.DATATYPE.UINT32, 0.001),  # looks like what we PULL from the battery
                Register(self, "LoadOutputEnergyThisHour", 0x0130, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "LoadOutputEnergyToday", 0x0134, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "LoadOutputEnergyThisWeek", 0x0138, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "LoadOutputEnergyThisMonth", 0x013C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatteryVoltage", 0x0050, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "BatteryCurrent", 0x0052, ModbusClientMixin.DATATYPE.INT32, 0.001),
                Register(self, "ChargeDCCurrent", 0x005C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "ChargeDCPower", 0x005E, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "ChargeDCPowerPercentage", 0x0060, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "GridACInputPower", 0x006C, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "GridOutputPowerW", 0x0084, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "GridOutputPowerVA", 0x008A, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "GeneratorACPower", 0x00AC, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "GeneratorACPowerApparent", 0x00BA, ModbusClientMixin.DATATYPE.UINT32),
                #Register(self, "LoadACPowerW", 0x009A, ModbusClientMixin.DATATYPE.UINT32),                     # equals to LoadACPowerApparent
                Register(self, "LoadACPowerApparent", 0x00A0, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "GridInputEnergyThisHour", 0x0100, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GridInputEnergyToday", 0x0104, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GridInputActiveToday", 0x0106, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "GridInputEnergyThisWeek", 0x0108, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GridInputEnergyThisMonth", 0x010C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GeneratorInputEnergyThisHour", 0x0148, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GeneratorInputEnergyToday", 0x014C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GeneratorInputActiveToday", 0x014E, ModbusClientMixin.DATATYPE.UINT32),
                Register(self, "GeneratorInputEnergyThisWeek", 0x0150, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                Register(self, "GeneratorInputEnergyThisMonth", 0x0154, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            ]

    def disconnect(self):
        pass

    def publish(self, dict):
        topic_soc = "xw-%s" % self.serial_number

        if self.registers != None:
            self.values.update(self.dump())
        dict[topic_soc] = self.values

    def formattedOutput(self):
        if self.registers != None:
            self.values.update(self.dump())

        loadACPowerApparent = self.values.get("LoadACPowerApparent",0)
        gridACInputPower = self.values.get("GridACInputPower",0)
        generatorACPowerApparent = self.values.get("GeneratorACPowerApparent",0)
        chargeDCPower = self.values.get("ChargeDCPower",0)
        efficiency = 0

        if gridACInputPower > 0 or generatorACPowerApparent > 0:
            efficiency = chargeDCPower/(gridACInputPower+generatorACPowerApparent-loadACPowerApparent)

        s = f"== Conext XW (id: {self.id} - serial: {self.serial_number}) ==\n"
        s += f"Active Power:\t\t{loadACPowerApparent:.2f}W\n"
        s += f'Input Power\t\tGrid: {gridACInputPower}W\tGenerator: {generatorACPowerApparent}W\n'
        s += f"Charge DC Power:\t{chargeDCPower:.2f}W\n"
        s += f'Efficiency\t\t{efficiency*100:.2f}%'

        return s