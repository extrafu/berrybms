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
from ModbusDevice import ModbusDevice
from Register import Register
from enum import Enum
import time

class ConextAGS(ModbusDevice):

    GeneratorModeOff = 0
    GeneratorModeOn = 1
    GeneratorModeAutomatic = 2
    GeneratorModeForceOnAutoOff = 3

    def __init__(self,
                id,
                connection=None):
        super().__init__(id)
        self.connection = connection

        if self.connection != None:
            self.registers = [
                Register(self, "FGANumber", 0x000A, ModbusClientMixin.DATATYPE.STRING, None, 10),
                #Register(self, "UniqueIDNumber", 0x0014, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "HardwareSerialNumber", 0x002B, ModbusClientMixin.DATATYPE.STRING, None, 10),
                Register(self, "GeneratorMode", 0x004D, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "GeneratorAutoStartOnBatterySOC", 0x0055, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "GeneratorAutoStopOnBatterySOC", 0x0056, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "SOCLevelStopGenerator", 0x0087, ModbusClientMixin.DATATYPE.UINT16),
                Register(self, "SOCLevelStartGenerator", 0x0088, ModbusClientMixin.DATATYPE.UINT16)
            ]

    def disconnect(self):
        pass

    # 0=Off
    # 1=On
    # 2=Automatic
    # 3=Force On Auto Off
    def setGeneratorMode(self, mode):
        register = self.getRegister("GeneratorMode")

        v = register.getValue(self.connection, True)

        if (v != mode):
            register.setValue(self.connection, mode)

    def publish(self, c):
       pass
    
    def formattedOutput(self):
        if self.registers != None:
            self.values.update(self.dump())

        generatorMode = self.values.get("GeneratorMode")
        socLevelStopGenerator = self.values.get("SOCLevelStopGenerator",0)
        socLevelStartGenerator = self.values.get("SOCLevelStartGenerator",0)

        s = f"== Conext AGS (id {self.id}) ==\n"
        s += f"Generator Mode:\t\t{generatorMode}\n"
        s += f"SOC Triggers\t\tStart: {socLevelStartGenerator}%\tStop: {socLevelStopGenerator}%"
        return s