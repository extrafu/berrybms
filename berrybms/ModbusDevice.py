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
import json

class ModbusDevice(object):

    def __init__(self, id):
        self.id = id
        self.connection = None

    def disconnect(self):
        if self.connection != None:
            #print("Closing connnection...")
            self.connection.close()

    def getAllRegisters(self):
        return self.registers

    # Return the initialized value of a register
    def getRegister(self, name):
        for register in self.registers:
            if name == register.name:
                register.getValue(self.connection)
                return register
        return None

    def dump(self):
        values = {}
        for register in self.registers:
            values[register.name] = register.getValue(self.connection)

        return values
    
    def __str__(self):
        json_formatted = json.dumps(self.dump(), indent=2)
        return  json_formatted
    
    def formattedOutput(self):
        return ""