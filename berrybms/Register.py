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

import pymodbus.exceptions # type: ignore
import pymodbus.payload # type: ignore
import time

class Register(object):

    def __init__(self,
            device,
            name,
            address,
            type,
            scale=1,
            length=0
            ):
        
        self.id = device.id
        self.values = device.values
        self.name = name
        self.address = address
        self.type = type
        self.scale = scale
        self.length = length
        self.values[name] = None

    def getValue(self, c, reload=False):

        if reload == True:
            self.values[self.name] = None

        if self.values[self.name] != None:
            return self.values[self.name]
        
        use_scale = True
        if self.type == ModbusClientMixin.DATATYPE.STRING:
            use_scale = False
        elif (self.type == ModbusClientMixin.DATATYPE.INT16 or self.type == ModbusClientMixin.DATATYPE.UINT16):
            self.length = 1
        elif (self.type == ModbusClientMixin.DATATYPE.INT32 or self.type == ModbusClientMixin.DATATYPE.UINT32):
            self.length = 2

        recv = c.read_holding_registers(address=self.address, count=self.length, slave=self.id)
        if not isinstance(recv, pymodbus.pdu.register_message.ReadHoldingRegistersResponse):
            return None

        self.values[self.name] = c.convert_from_registers(recv.registers, data_type=self.type)
        if use_scale:
            self.values[self.name] = self.values[self.name] * self.scale
  
        time.sleep(0.05)

        return self.values[self.name]

    def setValue(self, c, value):

        self.values[self.name] = value
        raw_value = c.convert_to_registers(value, self.type)
        r = c.write_registers(self.address, raw_value, slave=self.id)
        time.sleep(0.05)

        return r
