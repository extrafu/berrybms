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

import pymodbus.exceptions
import pymodbus.payload
import time

class Register(object):

    def __init__(self,
            id, 
            name,
            address,
            type,
            scale=1,
            length=0
            ):
        
        self.id = id
        self.name = name
        self.address = address
        self.type = type
        self.scale = scale
        self.length = length
        self.value = None

    def getValue(self, c, reload=False):

        if reload == True:
            self.value = None

        if self.value != None:
            return self.value
        
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

        self.value = c.convert_from_registers(recv.registers, data_type=self.type)
        if use_scale:
            self.value = self.value * self.scale
  
        time.sleep(0.05)

        return self.value

    def setValue(self, c, value):

        raw_value = c.convert_to_registers(value, self.type)
        r = c.write_registers(self.address, raw_value, slave=self.id)
        time.sleep(0.05)

        return r
