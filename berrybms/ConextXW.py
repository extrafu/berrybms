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
import pymodbus.client as ModbusClient
from pymodbus.client.mixin import ModbusClientMixin
import json

from ModbusDevice import ModbusDevice
from Register import Register

class ConextXW(ModbusDevice):

    def __init__(self,
                id,
                connection):
        super().__init__(id)
        self.connection = connection

        self.registers = [
            Register(self.id, "EnergyFromBatteryThisHour", 0x00D0, ModbusClientMixin.DATATYPE.UINT32, 0.001), # looks like what goes INTO the battery from AC1/AC2
            Register(self.id, "EnergyFromBatteryToday", 0x00D4, ModbusClientMixin.DATATYPE.UINT32, 0.001),    # looks like what goes INTO the battery from AC1/AC2
            Register(self.id, "BatteryDischargeActiveToday", 0x00D6, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "EnergyFromBatteryThisWeek", 0x00D8, ModbusClientMixin.DATATYPE.UINT32, 0.001), # looks like what goes INTO the battery from AC1/AC2
            Register(self.id, "EnergyFromBatteryThisMonth", 0x00DC, ModbusClientMixin.DATATYPE.UINT32, 0.001),# looks like what goes INTO the battery from AC1/AC2 
            Register(self.id, "EnergyToBatteryThisHour", 0x00E8, ModbusClientMixin.DATATYPE.UINT32, 0.001),   # looks like what we PULL from the battery
            Register(self.id, "EnergyToBatteryToday", 0x00EC, ModbusClientMixin.DATATYPE.UINT32, 0.001),      # looks like what we PULL from the battery
            Register(self.id, "BatteryChargeActiveToday", 0x00EE, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "EnergyToBatteryThisWeek", 0x00F0, ModbusClientMixin.DATATYPE.UINT32, 0.001),   # looks like what we PULL from the battery
            Register(self.id, "EnergyToBatteryThisMonth", 0x00F4, ModbusClientMixin.DATATYPE.UINT32, 0.001),  # looks like what we PULL from the battery
            Register(self.id, "LoadOutputEnergyThisHour", 0x0130, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "LoadOutputEnergyToday", 0x0134, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "LoadOutputEnergyThisWeek", 0x0138, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "LoadOutputEnergyThisMonth", 0x013C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatteryVoltage", 0x0050, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "BatteryCurrent", 0x0052, ModbusClientMixin.DATATYPE.INT32, 0.001),
            Register(self.id, "BatteryPower", 0x0054, ModbusClientMixin.DATATYPE.INT32),
            Register(self.id, "ChargeDCCurrent", 0x005C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "ChargeDCPower", 0x005E, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "ChargeDCPowerPercentage", 0x0060, ModbusClientMixin.DATATYPE.UINT16),
            Register(self.id, "GridACInputPower", 0x006C, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "GridOutputPowerW", 0x0084, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "GridOutputPowerVA", 0x008A, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "GeneratorACPower", 0x00AC, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "GeneratorACPowerApparent", 0x00BA, ModbusClientMixin.DATATYPE.UINT32),
            #Register(self.id, "LoadACPowerW", 0x009A, ModbusClientMixin.DATATYPE.UINT32),                     # equals to LoadACPowerApparent
            Register(self.id, "LoadACPowerApparent", 0x00A0, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "GridInputEnergyThisHour", 0x0100, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GridInputEnergyToday", 0x0104, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GridInputActiveToday", 0x0106, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "GridInputEnergyThisWeek", 0x0108, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GridInputEnergyThisMonth", 0x010C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GeneratorInputEnergyThisHour", 0x0148, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GeneratorInputEnergyToday", 0x014C, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GeneratorInputActiveToday", 0x014E, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "GeneratorInputEnergyThisWeek", 0x0150, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "GeneratorInputEnergyThisMonth", 0x0154, ModbusClientMixin.DATATYPE.UINT32, 0.001),
        ]

    def disconnect(self):
        return None

    def publish(self, dict):
        topic_soc = "xw-%d" % self.id
        dict[topic_soc] = self.dump()

    def formattedOutput(self):
        loadACPowerApparent = self.getRegister("LoadACPowerApparent").value
        gridACInputPower = self.getRegister("GridACInputPower").value
        generatorACPowerApparent = self.getRegister("GeneratorACPowerApparent").value
        chargeDCPower = self.getRegister("ChargeDCPower").value
        efficiency = 0

        if gridACInputPower > 0 or generatorACPowerApparent > 0:
            efficiency = chargeDCPower/(gridACInputPower+generatorACPowerApparent-loadACPowerApparent)

        s = f"== Conext XW (id {self.id}) ==\n"
        s += f"Active Power:\t\t{loadACPowerApparent:.2f}W\n"
        s += f'Input Power\t\tGrid: {gridACInputPower}W\tGenerator: {generatorACPowerApparent}W\n'
        s += f"Charge DC Power:\t{chargeDCPower:.2f}W\n"
        s += f'Efficiency\t\t{efficiency*100:.2f}%'

        return s