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
import json

from ModbusDevice import ModbusDevice
from Register import Register

class JKBMS(ModbusDevice):

    def __init__(self,
                 id,
                 port):
        super().__init__(id)
        self.port = port
        self.registers = [
            Register(self.id, "BatChargeEN", 0x1070, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "BatCurrent", 0x1298, ModbusClientMixin.DATATYPE.INT32, .001),
            Register(self.id, "BatDisChargeEN", 0x1074, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "BatVol", 0x12E4, ModbusClientMixin.DATATYPE.UINT16, .01),
            Register(self.id, "CellCount", 0x106C, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "CellVolAve", 0x1244, ModbusClientMixin.DATATYPE.UINT16, .001),
            Register(self.id, "HardwareVersion", 0x1410, ModbusClientMixin.DATATYPE.STRING, None, 4),
            Register(self.id, "ManufacturerDeviceID", 0x1400, ModbusClientMixin.DATATYPE.STRING, None, 8),
            Register(self.id, "SOCCapRemain", 0x12A8, ModbusClientMixin.DATATYPE.INT32, 0.001),
            Register(self.id, "SOCCycleCount", 0x12B0, ModbusClientMixin.DATATYPE.UINT32),
            Register(self.id, "SOCFullChargeCap", 0x12AC, ModbusClientMixin.DATATYPE.UINT32, 0.001),
            Register(self.id, "SOCStateOfcharge", 0x12A6, ModbusClientMixin.DATATYPE.UINT16),
            Register(self.id, "SoftwareVersion", 0x1418, ModbusClientMixin.DATATYPE.STRING, None, 4),
            Register(self.id, "Alarms", 0x12A0, ModbusClientMixin.DATATYPE.UINT32)
        ]
        self.cellVoltages = None
    
    def connect(self):
        if self.connection == None:
            self.connection = ModbusClient.ModbusSerialClient(port=self.port, stopbits=1, bytesize=8, parity='N', baudrate=115200, timeout=1)
            if self.connection.connect():
                print("Successfully connected to BMS id %d" % self.id)
            else:
                print("Cannot connect to BMS id %d" % self.id)
                self.connection = None 

        return self.connection

    def setChargeMode(self, mode):
        register = self.getRegister("BatChargeEN")
        register.setValue(self.connection, mode)

    def setDischargeMode(self, mode):
        register = self.getRegister("BatDisChargeEN")
        register.setValue(self.connection, mode)

    def getCellVoltages(self, reload=False):
        if self.cellVoltages == None or reload == True:
            count = self.getRegister('CellCount').value
            values = []

            recv = self.connection.read_holding_registers(address=0x1200, count=count, slave=self.id)
            if not isinstance(recv, pymodbus.pdu.register_message.ReadHoldingRegistersResponse):
                return None
            
            values = self.connection.convert_from_registers(recv.registers, data_type=self.connection.DATATYPE.UINT16)

            for i in range(0, count):
                r = Register(self.id, f'CellVol{i}', 0x1200+i*2, ModbusClient.ModbusSerialClient.DATATYPE.UINT16, 0.001)
                r.value = round(values[i]*0.001,3)
                values[i] = r.value
                self.registers.append(r)
            
            self.cellVoltages = values

        return self.cellVoltages

    def publish(self, dict):
        topic_soc = "bms-%d" % self.id
        dict[topic_soc] = self.dump()

    def __str__(self):
        self.getCellVoltages()
        return super().__str__()
    
    def formattedOutput(self):
        bms_model = self.getRegister('ManufacturerDeviceID').value
        bms_hw_version = self.getRegister('HardwareVersion').value
        bms_sw_version = self.getRegister('SoftwareVersion').value
        alarms = self.getRegister('Alarms').value
        
        # We skip the first byte, as it can be 0, 1 and 2
        # A 100% SOC will give us a value of 100 with first byte set to 0, 356 when set to 1 and 612 when set to 2
        soc = self.getRegister('SOCStateOfcharge').value & 0x0FF
        cycle_count = self.getRegister('SOCCycleCount').value
        pack_voltage = self.getRegister('BatVol').value
        cell_count = self.getRegister('CellCount').value
        cell_avg_voltage = self.getRegister('CellVolAve').value
        battery_current = self.getRegister('BatCurrent').value
        discharge_enabled = self.getRegister('BatDisChargeEN').value
        pack_capacity = self.getRegister('SOCFullChargeCap').value
        pack_remaining = self.getRegister('SOCCapRemain').value

        s = f"== JK BMS (id {self.id}) - {bms_model} (v{bms_hw_version}) - sw v{bms_sw_version}) ==\n"          
        s += f"Alarms?\t\t\t{alarms}\n"
        s += f"SOC:\t\t\t{soc} ({cycle_count} cycle(s))\n"
        s += f"Voltage:\t\t{pack_voltage:.2f}v\n"
        s += "Cell voltages:\t\t%s\n" % (str(self.getCellVoltages()))
        s += f"Cell average voltage:\t{cell_avg_voltage:.3f} ({cell_count} cells)\n"
        s += "Battery current:\t%.3f (%s %.2f Wh)\n" % (battery_current, ("charging" if battery_current > 0 else "discharging"), pack_voltage*battery_current)
        s += f"Discharge enabled?\t{discharge_enabled}\n"
        s += f"Remaining Ah capacity:\t{pack_remaining:.2f} ({pack_capacity} Ah capacity)"

        return s
