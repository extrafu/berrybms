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
import json

from ModbusDevice import ModbusDevice
from Register import Register

class JKBMS(ModbusDevice):

    def __init__(self,
                 name,
                 id,
                 port=None):
        super().__init__(id)
        self.name = name
        self.port = port
        self.cellVoltages = None
    
    def connect(self):
        if self.connection == None:
            self.connection = ModbusClient.ModbusSerialClient(port=self.port, stopbits=1, bytesize=8, parity='N', baudrate=115200, timeout=2)
            if self.connection.connect():
                print("Successfully connected to BMS id %d" % self.id)
                self.registers = [
                    Register(self, "BatChargeEN", 0x1070, ModbusClientMixin.DATATYPE.UINT32),
                    Register(self, "BatDisChargeEN", 0x1074, ModbusClientMixin.DATATYPE.UINT32),
                    Register(self, "BatCurrent", 0x1298, ModbusClientMixin.DATATYPE.INT32, .001),
                    Register(self, "BatVol", 0x12E4, ModbusClientMixin.DATATYPE.UINT16, .01),
                    Register(self, "CellCount", 0x106C, ModbusClientMixin.DATATYPE.UINT32),
                    Register(self, "CellVolAve", 0x1244, ModbusClientMixin.DATATYPE.UINT16, .001),
                    Register(self, "HardwareVersion", 0x1410, ModbusClientMixin.DATATYPE.STRING, None, 4),
                    Register(self, "ManufacturerDeviceID", 0x1400, ModbusClientMixin.DATATYPE.STRING, None, 8),
                    Register(self, "DevAddr", 0x1108, ModbusClientMixin.DATATYPE.UINT32),
                    Register(self, "SOCCapRemain", 0x12A8, ModbusClientMixin.DATATYPE.INT32, 0.001),
                    Register(self, "SOCCycleCount", 0x12B0, ModbusClientMixin.DATATYPE.UINT32),
                    Register(self, "SOCFullChargeCap", 0x12AC, ModbusClientMixin.DATATYPE.UINT32, 0.001),
                    Register(self, "SOCStateOfcharge", 0x12A6, ModbusClientMixin.DATATYPE.UINT16),
                    Register(self, "SoftwareVersion", 0x1418, ModbusClientMixin.DATATYPE.STRING, None, 4),
                    Register(self, "Alarms", 0x12A0, ModbusClientMixin.DATATYPE.UINT32)
                ]
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
        if self.connection == None:
            return

        if self.cellVoltages == None or reload == True:
            count = self.getRegister('CellCount').value
            values = []

            recv = self.connection.read_holding_registers(address=0x1200, count=count, slave=self.id)
            if not isinstance(recv, pymodbus.pdu.register_message.ReadHoldingRegistersResponse):
                return None
            
            values = self.connection.convert_from_registers(recv.registers, data_type=self.connection.DATATYPE.UINT16)

            for i in range(0, count):
                r = Register(self, f'CellVol{i}', 0x1200+i*2, ModbusClient.ModbusSerialClient.DATATYPE.UINT16, 0.001)
                r.value = round(values[i]*0.001,3)
                values[i] = r.value
                self.registers.append(r)
            
            self.cellVoltages = values

        return self.cellVoltages

    def publish(self, dict):
        topic_soc = "bms-%d" % self.id

        if self.registers != None:
            self.values.update(self.dump())

        self.values["name"] = self.name
        dict[topic_soc] = self.values

    def __str__(self):
        self.getCellVoltages()
        return super().__str__()
    
    def formattedOutput(self):
        if self.registers != None:
            self.values.update(self.dump())

        bms_model = self.values.get('ManufacturerDeviceID')
        bms_hw_version = self.values.get('HardwareVersion')
        bms_sw_version = self.values.get('SoftwareVersion')
        dev_addr = self.values.get('DevAddr')
        alarms = self.values.get('Alarms', 0)
        
        # We skip the first byte, as it can be 0, 1 and 2
        # A 100% SOC will give us a value of 100 with first byte set to 0, 356 when set to 1 and 612 when set to 2
        soc = self.values.get('SOCStateOfcharge', 0) & 0x0FF
        cycle_count = self.values.get('SOCCycleCount', 0)
        pack_voltage = self.values.get('BatVol', 0)
        cell_count = self.values.get('CellCount', 0)
        cell_avg_voltage = self.values.get('CellVolAve', 0)
        battery_current = self.values.get('BatCurrent', 0)
        discharge_enabled = self.values.get('BatDisChargeEN', 0)
        pack_capacity = self.values.get('SOCFullChargeCap', 0)
        pack_remaining = self.values.get('SOCCapRemain', 0)
        status = "charging" if battery_current > 0 else "discharging"

        s = f"== {self.name} (id {self.id}) - {bms_model} (v{bms_hw_version}) - sw v{bms_sw_version} dev_addr: {dev_addr}) ==\n"
        s += f"Alarms?\t\t\t{alarms}\n"
        s += f"SOC:\t\t\t{soc} ({cycle_count} cycle(s))\n"
        s += f"Voltage:\t\t{pack_voltage:.2f}v\n"
        s += f"Cell Voltages:\t\t{str(self.getCellVoltages())}\n"
        s += f"Cell Average Voltage:\t{cell_avg_voltage:.3f} ({cell_count} cells)\n"
        s += f"Battery Current:\t{battery_current:.3f}A ({status} {pack_voltage*battery_current:.2f}W)\n"
        s += f"Discharge Enabled?\t{discharge_enabled}\n"
        s += f"Remaining Capacity:\t{pack_remaining:.2f}Ah ({pack_capacity}Ah capacity)"

        return s
