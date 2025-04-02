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
from datetime import datetime
from time import mktime

from ModbusDevice import ModbusDevice

class ConextSCP(ModbusDevice):

    def __init__(self,
                id,
                connection=None):
        super().__init__(id)
        self.connection = connection
        self.values = {}

    def disconnect(self):
        pass

    def publish(self, c):
        pass
    
    def formattedOutput(self):
        current_datetime = self.values.get("CurrentDateTime", None)
        value = ""

        if current_datetime != None:
            value = datetime.fromtimestamp(mktime(current_datetime))

        s = f"== Conext SCP (id {self.id}) ==\n"
        s += f'Current datetime:\t{value}'
        return s