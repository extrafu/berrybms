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
import can # type: ignore
import binascii
import struct
import time
import sys
import logging
import socket

import paho.mqtt.client as paho # type: ignore
import json
import yaml # type: ignore

from ConextAGS import ConextAGS
from ConextBattMon import ConextBattMon
from ConextInsightHome import ConextInsightHome
from ConextMPPT import ConextMPPT
from ConextSCP import ConextSCP # type: ignore
from ConextXW import ConextXW

from Nmea2000 import Iso11783Decode, Iso11783Encode
from XanbusMessage import XanbusMessage

class XanbusSniffer(object):

    def __init__(self,
                config,
                logger):
            
        self.config = config
        self.logger = logger
        self.all_xanbus_devices = dict()
        self.unknown_bytes = bytearray()
        self.xanbus_queue = dict()
    
    def processBattMonSts(self, src, bytes):
        # TODO: decode voltage midpoints and remaining data
        # b'0303 d6d30000 f4640100 6874 9500 2f04 58 ff 8504 fffffffffffcff0000000000000000ffffff7fffff'
        #print(f'ConextBattMonStats: src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        
        f ='<BBIiHHHbbH21x'
        fields = struct.unpack(f, bytes)
        (status,assoc,voltage,current,battery_temperature,capacity_removed,capacity_remaining,soc,pad6,time_to_discharge) = fields

        #print(f'src={src} BATTMON voltage={voltage/1000}v current={current/1000}A battery_temperature={battery_temperature/1000}C capacity_removed={capacity_removed}Ah capacity_remaining={capacity_remaining}Ah soc={soc}% time_to_discharge={time_to_discharge}mins')
        #print(f'{pad1:x} {pad2:x} {pad3:x} {pad6:x}')

        battmon = self.all_xanbus_devices[src]
        battmon.values["BatteryVoltage"] = voltage/1000
        battmon.values["BatteryCurrent"] = current/1000
        battmon.values["BatteryCapacityRemoved"] = capacity_removed
        battmon.values["BatteryCapacityRemaining"] = capacity_remaining
        battmon.values["BatterySOC"] = soc

    # Shared with XW+/MPPT
    def processBattSts2(self, src, bytes):
        #print(f'{processBattSts2.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # MPPT: b'0303 90d30000 98710000 26060000 ffff ffff 00ff ff41 ffffffffffffffffffffffff0330ffffffffff'
        # XW:   b'0303 f0d20000 9cebffff 19010000 ffff ffff 00ff ff56 ffffffffffffffffffffffffffffffffffffff'
        (status,assoc,voltage,current,power) = struct.unpack('<BBIii27x', bytes)
        #print(f'src={src} DC USAGE: voltage={voltage/1000}v current={current/1000}A power={power}W')

    def processAcStsRms(self, src, bytes):
        # assoc == 13  -> AC2 in
        # assoc == 33  -> AC Out/Loads
        # assoc == 43  -> AC1 in/out (grid)
        status = int(bytes[0])
        assoc = int(bytes[1])
        xw = self.all_xanbus_devices[src]

        if len(bytes) == 55:
            #print(f'assoc = {assoc}')
            if assoc == 0x13 or assoc == 0x33:
                #print(f'{processAcStsRms.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
                # b'03 33 fc 01 ff 58d80100   be05        00 00 04 6f17 ffff 1601 00 00 1601 00 00 04 7f 02 ff 58d80100      e812        00 00 10 6f17   ffff  9f02  0000 9f02 0000 0a 7fffff'
                # b'03 33 fc 01 ff dad30100   040b        00 00 09 6e17 ffff b501 00 00 b501 00 00 06 7f 02 ff dad30100      460a        00 00 08 6e17   ffff  a401  0000 a401 0000 06 7fffff'
                # b'03 13 fc 01 04 52c00100   4269        ff ff ff 6d17 7017 abee ff ff 85ee ff ff ff 7f 02 04 58bf0100      8869        ff ff ff ffff   7017  c9ee  ffff b6ee ffff ff 7fffff' -- gen on
                # b'03 13 fc 01 04 5cc00100   b67c        ff ff ff 6a17 7017 f7f0 ff ff c2f0 ff ff ff 7f 02 04 66c00100      aa7e        ff ff ff ffff   7017  27f1  ffff 0df1 ffff ff 7fffff' -- gen on
                # b'03 13 fc 01 04 32c20100   7a7c        ff ff ff 7017 7017 dbf0 ff ff cef0 ff ff ff 7f 02 04 88c10100      e27d        ff ff ff ffff   7017  09f1  ffff 09f1 ffff ff 7fffff' -- gen on
                # b'03 33 fc 01 ff 9cda0100   9c04        00 00 03 7017 ffff b600 00 00 b600 00 00 02 7f 02 ff 9cda0100      a604        00 00 03 7017   ffff  e000  0000 e000 0000 03 7fffff'
                # b'03 33 fc 01 ff 2ecb0100   4006        00 00 05 6f17 ffff 1401 00 00 1401 00 00 04 7f 02 ff 2ecb0100      1603        00 00 02 6f17   ffff  b600  0000 b600 0000 02 7fffff'
                # b'03 33 fc 01 ff 42d50100   c206        00 00 05 7017 ffff f900 00 00 f900 00 00 03 7f 02 ff 42d50100      cc06        00 00 05 7017   ffff  2301  0000 2301 0000 04 7fffff'
                #                  LOAD_V_LN1 LOAD_I_LN1           GF1  GF2  p11        p15                    LOAD_V_LN_2   LOAD_I_LN2           LOAD_F AC2_F pad28      pad30
                #   B  B  B  B  B  I          h           B  B  B  h    h    h     B  B  h     B  B  B  B  B  B  I             h           B  B  B  h      h     H     h    H
                (status,assoc,p1,p2,p3,load_v_ln1,load_i_ln1,p4,p5,p6,gen1_f,gen2_f,p11,p13,p14,p15,p17,p18,p19,p20,p21,p22,load_v_ln2,load_i_ln2,p25,p26,p27,load_f,ac2_f,pad28,pad29,pad30) = struct.unpack('<5BIh1BBBhhhBBh6BIhBBBhhHhH6x', bytes)
                load_i = load_i_ln1+load_i_ln2
                load_p = p11+pad28

                if assoc == 0x33:
                    xw.values["LoadACPowerApparent"] = load_p
                else:
                    xw.values["GeneratorACPowerApparent"] = load_p

                #print(f'load_p={load_p} gen1_f={gen1_f} gen2_f={gen2_f}') # when assoc == 13, we have 2 freq, otherwise load_f == gen1_f
                #print(f'src={src} load_v_ln1={load_v_ln1/1000}v load_i_ln1={load_i_ln1/1000}A load_v_ln2={load_v_ln2/1000}v load_i_ln2={load_i_ln2/1000}A load_f={load_f} ac2_f={ac2_f} load_i={load_i/1000}A load_p={load_p:.0f}W p11={p11} p15={p15} pad28={pad28} pad29={pad30}')
                #if assoc == 0x13:
                #    sys.exit(0)
        else:
            #print(f'{processAcStsRms.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
            # 83 bytes, ASSOC_CFG_AC_INPUT_response
            #b'03 43 fc 01 01 0000000000000000ff000070170000000000000000ff7f02010000000000000000ff000070170000000000000000ff7f030100000000ffffff7fff00007017ffffffffffffffffff7fffffffffff'
            #b'03 43 fc 01 01 0000000000000000ff000070170000000000000000ff7f02010000000000000000ff000070170000000000000000ff7f030100000000ffffff7fff00007017ffffffffffffffffff7fffffffffff' -- gen off
            #b'03 43 fc 01 01 0000000000000000ff000070170000000000000000ff7f02010000000000000000ff000070170000000000000000ff7f030100000000ffffff7fff00007017ffffffffffffffffff7fffffffffff' -- gen on
            #                 LOAD_V_LN1 LOAD_I_LN1           GF1  GF2  p11        p15                    LOAD_V_LN_2   LOAD_I_LN2           LOAD_F AC2_F pad28      pad30               extra bytes from ac1 (grid)
            #b'03 43 fc 01 04 40d70100   5083        ff ff ff 9417 7017 e9f0 ff ff eaf0 ff ff ff 7f 02 04 80d80100      9a89        ff ff ff 9417   7017  adf1  ffff 75f1 ffff ff 7f0304 12b80300ffffff7fff94177017ffffffffffffffffff7fffffffffff' -- grid on (or gen2)
            #(state,assoc) = struct.unpack('<BB81x', bytes)
            buffer1 = bytes[0:55]

            (status,assoc,p1,p2,p3,ac1_in_v_ln1,ac1_i_ln1,p4,p5,p6,gen1_f,gen2_f,p11,p13,p14,p15,p17,p18,p19,p20,p21,p22,ac1_in_v_ln2,ac1_i_ln2,p25,p26,p27,load_f,ac2_f,pad28,pad29,pad30) = struct.unpack('<5BIh1BBBhhhBBh6BIhBBBhhhhH6x', buffer1)
            ac1_in_i = ac1_i_ln1+ac1_i_ln2
            ac1_in_p = p11+p15

            xw.values["GridACInputPower"] = ac1_in_p

            # 12b80300 ff ff ff 7f ff 9417 7017 ffffffffffffffffff7fffffffffff  (remaining part, 28 bytes)
            buffer2 = bytes[55:83]
            (load_v,pad,pad,pad,pad,pad,ac1_in_f,acX_in_f) = struct.unpack('<IBBBBBhh15x', buffer2)

            #print(f'gen1_f={gen1_f} gen2_f={gen2_f}') # gen1_f == load_f == ac1_in_f
            #print(f'src={src} ac1_in_v_ln1={ac1_in_v_ln1/1000}v ac1_i_ln1={ac1_i_ln1/1000}A ac1_in_v_ln2={ac1_in_v_ln2/1000}v ac1_i_ln2={ac1_i_ln2/1000}A load_f={load_f} ac2_f={ac2_f} ac1_in_i={ac1_in_i/1000}A ac1_in_p={ac1_in_p:.0f}W p11={p11} p15={p15} pad28={pad28} pad29={pad29} pad30={pad30}')
            #print(f'src={src} load_v={load_v} ac1_in_f={ac1_in_f} acX_in_f={acX_in_f}')
            #print(f'assoc = {assoc:x}')
            #sys.exit(0)


    # DC statistics (charging battery and PV input)
    def processDcSrcSts2(self, src, bytes):
        device = self.all_xanbus_devices[src]
        
        #print(f'processDcSrcSts2: src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        (status,assoc,voltage,current,power) = struct.unpack('<BBIii13x', bytes)
        #print(f'src={src} DC batt voltage={voltage/1000}v current={current/1000}A power={power}W')

        # DC output - what is going to the battery
        if assoc == 0x03:
            # XW's DC connection (to the battery) - charging from generator or pulling from battery
            # TODO: why is power positive when discharging?
            if isinstance(device, ConextXW):
                device.values["ChargeDCCurrent"] = current/1000
                device.values["ChargeDCPower"] = power*-1

            # MPPT to the battery - charging from PV
            # TODO: why is current negative?
            else:
                device.values["DCOutputVoltage"] = voltage/1000
                device.values["DCOutputCurrent"] = abs(current/1000)
                device.values["DCOutputPower"] = power

        # DC input - MPPT: what's coming from the solar panels
        if assoc == 0x15:
            # b'0315 40110400 e2130000 4c050000 9f03 0000 fc0000ffffffffffff'
            #(state,op,voltage,current,power, pad3, pad4) = struct.unpack('<BBIiIBB11x', bytes)
            #print(f'processDcSrcSts2: src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
            #print(f'src={src} PV_input_voltage={voltage/1000}v PV_current={current/1000}A PV_power={power}W')
            #print(f'pad3={pad3:b} pad4={pad4:b}')
            device.values["PVVoltage"] = voltage/1000
            device.values["PVCurrent"] = abs(current/1000)
            device.values["PVPower"] = power
            #print(f'processDcSrcSts2: src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
            #b'0315 d6e70500 d8040000 df010000 3f050000fc00150315d6e70500'
            #b'0315 c0d00500 56e1ffff a6010015 0315c0d00500d8040000d80100'
            #print(power)

    def processSpsSts(self, src, bytes):
        # b'0300ffffff7fffffff7f0d010001ffffffffffff' -- gen on
        #print(f'{processSpsSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        pass

    # See https://github.com/xela144/CANaconda/blob/master/metadata/Xanbus.xml  
    def processChgSts(self, src, bytes):
        #print(f'{processChgSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        #b'0303 50 dc 00 00 50 40 01 00 03 01 0103 02 c100ffffff' - mppt
        #b'0303 50 dc 00 00 50 40 01 00 05 01 0103 02 c100ffffff' - mppt
        #b'0303 50 dc 00 00 50 40 01 00 02 01 0103 02 c100ffffff' - mppt
        #b'0303 50 dc 00 00 50 40 01 00 03 01 0103 01 c100ffffff' - mppt
        #b'0303 50dc 0000 5040 0100 0b01 010302c100ffffff'
        #b'0303 00 00 00 00 00 00 00 00 00 02 0903 01 c1 ffffffff' - xw
        #b'0303 7c dd 00 00 e0 22 02 00 52 02 0103 01 c1 ffffffff' - xw with gen on
        # TODO: decode the rest! --> 03, 05, 02
        #       chg_en_sts doesn't exist for the XW+ so it's likely not that value we are decoding
        # chg_mode = 1 == primary, 2 == secondary
        (status,assoc,pad1,pad2,pad3,pad4,pad5,pad6,pad7,pad8,pad9,chg_en_sts,chg_sts,chg_mode) = struct.unpack('<BBBBBBBBBBBBHB5x', bytes)

        # chg_mode == 769 -> bulk, 770 -> absorb, 773 -> float,  see modbus doc, 777=qualifying ac
        #print(f'src={src} chg_en_sts={chg_en_sts} chg_sts={chg_sts} chg_mode={chg_mode}')

    def processInvSts2(self, src, bytes):
        #print(f'{processInvSts2.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # b'03 33 0004 f1 15 00 fe'
        # b'03 43 0004 f1 15 10 fe'
        # b'03 33 0104 f1 15 00 fe' -- with gen on
        # b'03 43 0104 f1 15 10 fe' -- with gen on
        (status,assoc,inverter_status,pad,inverter_configuration) = struct.unpack('<BBHBB2x', bytes)
        #inverter_status: 1024 == Invert, 1025 == AC Pass Through, see modbus doc "Section 10: Inverter Status"
        #inverrer_configuration: 21 (0x15) == Split Phase Master see Section 18: Conext XW/XW+ Inverter Configuration
        #print(f'src={src} assoc={assoc:x} inverter_status={inverter_status} inverter_configuration={inverter_configuration}')

    # DONE!
    def processDateTimeSts(self, src, bytes):
        #print(f'{processDateTimeSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # b'03 da4d9267 d4fefd'
        (status,d,offset) = struct.unpack('<BIhx', bytes)
        current_date = time.gmtime(d+(offset*60))
        self.all_xanbus_devices[src].values['CurrentDateTime'] = current_date
        #print(current_date)


    def processAgsSts(self, src, bytes):
        #print(f'{processAgsSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        #b'03 13 0b 01 0a              00           10 00 00 fc ffffff'
        #b'03 13 0b 01 0a              00           10 00 00 fc ffffff'
        #b'03 13 0b 01 0a              00           10 00 00 fc ffffff'
        #              ^- gen action   ^- on reason ^- gen off reason
        # TODO: decode gen_state? fault/warnings? 00/00
        # gen_action: 10 == stopped, 9 == runnning, see Section 4: Generator Actions
        # gen_on/off reasons: see Section 5: Generator On Reason/Section 6: Generator Off Reasons
        (status,assoc,pad,pad,gen_action,on_reason,off_reason) = struct.unpack('<BBBBBBB6x', bytes)
        #print(f'src={src} gen_action={gen_action} on_reason={on_reason} off_reason={off_reason}')

    def processUnknown2(self, src, bytes):
        # We seem to sometimes get shorter and different responses
        #if len(bytes) != 118:
        #    return

        if src == 2:
            if repr(bytes) != repr(self.unknown_bytes):
                #print(f'{processUnknown2.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
                #print(f'previous={binascii.hexlify(unknown_bytes)}')
                #print(f'new={binascii.hexlify(bytes)}')
                self.unknown_bytes = bytes
                #(state,op,pad1,pad2,pad3,pad4,pad5,pad6,pad7,pad8,pad9,pad10,pad11,pad12,dc_out_energy_day,pad13,pad14,pad15,pad16,pad17,pad18,pad19,pad20,dc_out_energy_month) = struct.unpack('<BBIIIIIIIIIIIIIIIIIIcccI37x', bytes)
                (status,assoc,pad1,pad2,pad3,pad4,pad5,pad6,pad7,pad8,pad9,pad10,pad11,pad12,dc_out_energy_day,pad13,pad14,pad15,pad16,pad17,pad18,pad19,pad20,dc_out_energy_month) = struct.unpack('<BBIIIIIIIIIIIIIIIIIIcccI37x', bytes)
                #print(f'src={src} dc_out_energy_day={dc_out_energy_day} dc_out_energy_month={dc_out_energy_month}')
                #print(f'pad5={hex(pad5)} pad6={pad6}')

    def processProdInfoSts(self, src, bytes):
        #print(f'{processProdInfoSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # b'07 58572041475300000000000000000000 3836352d313036302d303100 ffff ffffffffffffffffffffffffffffffffff' -- AGS
        # b'07 426174744d6f6e000000000000000000 3836352d313038302d303100 ffff ffffffffff7fffffffffffffffffffffff' -- BattMon
        # b'07 5857204d505054383000000000000000 3836352d3130333200000000 c012 0000 2c93 0900 80bb 0000 ffffffffffffff' -- MPPT 2
        # b'07 5857204d505054383000000000000000 3836352d3130333200000000 c012 0000 2c93 0900 80bb 0000 ffffffffffffff' -- MPPT 1
        # b'07 5857363834382d303100000000000000 3836352d363834382d303100 0019 0000 80bb 0000 c0d4 0100 7017 ffffffffff' -- XW+
        device_name = bytes[1:17].decode("UTF-8").replace('\x00','')
        device_fga = bytes[17:29].decode("UTF-8").replace('\x00','')
        #print(f'device_name={device_name} device_fga={device_fga}')
        #device = None

        clazz = ConextInsightHome.ConextProductMap.get(device_fga, None)
        if clazz == None:
            print(f"Unknown Conext device {device_fga}")
            sys.exit(1)

        device = clazz(src)
        self.all_xanbus_devices[src] = device

    def processHwRevSts(self, src, bytes):
        #print(f'{processHwRevSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # b'07 01 00 e0 01 00 42313331313733333000 d0a1dca9d0a1ffffffffff' -- BattMon
        # b'07 ff ff e0 ff ff 30303030313844373032443400 000000 ffffffffff' -- AGS
        # b'07 ff ff e0 05 00 30303030313542363232434200 000000 ffffffffff' -- MPPT 1
        # b'07 ff ff e0 05 00 30303030313542363735393200 000000 ffffffffff' -- MPPT 2
        # b'07 ff ff e0 ff ff 30303030313834443934384100 af3f1f ffffffffff' -- XW+
        serial_number = bytes[6:bytes.index(0x00,6)].decode("UTF-8")
        #print(f'serial_number={serial_number}')
        device = self.all_xanbus_devices[src]
        device.serial_number = serial_number

    def processSwVerSts(self, src, bytes):
        #print(f'{processSwVerSts.__name__} src = {src} len = {len(bytes)} bytes={binascii.hexlify(bytes)}')
        # b'07 f0 02 dc 50 00 00 04 00 f0 00 a1 28 00 00 b403 f003 10 2700 0006 00 ff ff' -- XW+
        #  dc50 -> 50dc = 20700 -> 2.07.00, 04 - bn4
        # b'07 f0 02 74 27 00 00 64 00 f0 00 a1 28 00 00 ac03 f003 66 0000 0008 00 ff ff' -- BattMon
        #  7427 -> 2774 -> 10100 -> 1.01.00, 64 - bn100
        pass

    def processXanbusMessage(self, xanbus_message):
        pgn = xanbus_message.pgn
        src = xanbus_message.src
        dst = xanbus_message.dst
        pri = xanbus_message.pri
        buffer = xanbus_message.bytes()

        # We check if we are still in discovery mode for the Xanbus device we
        # just received a message for to process. If that's the case we discard
        # what we received until our Xanbus device object is properly initialized
        if self.all_xanbus_devices[src] == True and pgn != 0x1F014:
            return

        match pgn:
            # ALL / Sts -- status?
            case 0x1F00F:
                return
                #print(f'{pgn:x} {src} {binascii.hexlify(buffer)}')

            # XW+ / AcStsRms
            # Collides with standardized "PGN: 126998 - Configuration Information"
            case 0x1F016:
                #return
                self.processAcStsRms(src, buffer)
    
            # XW+ / AcXferSwSts (useless?)
            # 03 20 03 01 -- gen off
            # 03 22 03 02 -- when gen is on
            case 0x1F0BF:
                return
                print(f'{pgn} {src} {binascii.hexlify(buffer)}')

            # XW+ / InvSts2  (inverter status?)
            case 0x1F0BD:
                #return
                self.processInvSts2(src, buffer)

            # XW+/MPPT / DcSrcSts2
            case 0x1F0C5:
                #return
                self.processDcSrcSts2(src, buffer)

            # XW+/MPPT / BattSts2
            case 0x1F0C4:
                #return
                self.processBattSts2(src, buffer)

            # XW+/MPPT / SpsSts
            # Sps == {sensor,secondary} power supply? // Smart Production Solution?
            # same data over and over?
            case 0x1F0C6:
                #return
                self.processSpsSts(src, buffer)

            # XW+/MPPT / ChgSts -- charger status
            # First value is 56400 which looks like 56.4v
            case 0x1F00E:
                #return
                self.processChgSts(src, buffer)

            # BattMon / BattMonSts
            case 0x1F01B:
                #return
                self.processBattMonSts(src, buffer)

            # AGS / AgsSts
            case 0x1F011:
                #return
                self.processAgsSts(src, buffer)

            # SCP/XW+/InsightHome(src==6) / DateTimeSts
            # Non-standard date-format
            case 0x1F809:
                #return
                self.processDateTimeSts(src, buffer)

            case 0x1F014:
                self.processProdInfoSts(src, buffer)

            case 0x1F810:
                self.processHwRevSts(src, buffer)

            case 0x1F80E:
                self.processSwVerSts(src, buffer)

        
            #
            # UNDOCUMENTED STUFF
            #

            # MPPT data - looks like data produced per hour/day/week...
            # No data is being sent by the XW+ even the generator is on
            case 0x1F0BE:
                #return
                self.processUnknown2(src, buffer)
            
            # coming only from MPPT?
            # Single packet, weird sequence over and over
            # 2nd by changes, but 3rd and 4th are relatively static
            case 0x1F00D:
                return
                print(f'{pgn} {src} {dst} {binascii.hexlify(buffer)}')

            # coming from XW only?
            # weird sequence, over and over
            # no data received when gen is on?!?
            case 0x1F01D:
                return
                print(f'{pgn} {src} {dst} {binascii.hexlify(buffer)}')

            # coming from MPPT? - looks like we get 0301 all the time
            # maybe just status info
            case 0x1F0C9:
                return
                print(f'{pgn} {src} {dst} {binascii.hexlify(buffer)}')

            # src == 0 - that's the SCP
            # We get 030105 all the time, also maybe just status info
            case 0x1F01C:
                return
                print(f'{pgn} {src} {dst} {binascii.hexlify(buffer)}')

            # Sent by XW6848 Pro only
            case 0x1DC00:
                return
                print(f'{pgn} {src} {dst} {binascii.hexlify(buffer)}')


            # unknown: 75008 1 0 Timestamp: 1737842977.896904    ID: 19250001    X Rx                DL:  4    10 00 83 03                 Channel: can0
            # unknown: 75008 1 0 Timestamp: 1737842977.906757    ID: 19250001    X Rx                DL:  4    10 00 85 13                 Channel: can0
            # unknown: 75008 1 0 Timestamp: 1737842977.916757    ID: 19250001    X Rx                DL:  4    10 00 86 33                 Channel: can0
            # unknown: 75008 1 0 Timestamp: 1737842977.926593    ID: 19250001    X Rx                DL:  4    10 00 87 43                 Channel: can0
            # AssocCfg
            case 0x12500:
                return
                print(f'{pgn} {src} {dst} {pri} {binascii.hexlify(buffer)}')
            #
            # Standard stuff
            #
            # STD: ISO Acknowledgement
            # 59392
            case 0xE800:
                return
                print(f'ISO Ack: {pgn} {src} {dst} {binascii.hexlify(buffer)}')
                
            # STD: ISO Request
            # 59904 0 3 Timestamp: 1737842084.946513    ID: 18ea0300    X Rx                DL:  3    be f0 01                    Channel: can0
            # See https://www.csselectronics.com/pages/j1939-explained-simple-intro-tutorial#j1939-request-messages for an excellent documentation
            case 0xEA00:
                return
                print(f'ISO Request: {pgn} {src} {dst} {binascii.hexlify(buffer)}')
        
            # STD: ISO Address Claim
            case 0xEE00:
                return
                print(f'ISO Address Claim: {pgn} {src} {dst} {pri} {binascii.hexlify(buffer)}')
                
            case _:
                #continue
                print(f'unknown: {pgn} {src} {dst} {pri} {binascii.hexlify(buffer)}')
                return


    def sniff(self):
        paho_client = paho.Client()
        if self.config['conext']['xanbus_sniffer'].get("host", None) != None:
            bus = can.interface.Bus(interface='socketcand',
                                    host=self.config['conext']['xanbus_sniffer']['host'],
                                    port=self.config['conext']['xanbus_sniffer']['port'],
                                    channel=self.config['conext']['xanbus_sniffer']['channel'])
        else:
            bus = can.ThreadSafeBus(interface='socketcan',
                                    channel=self.config['conext']['xanbus_sniffer']['channel'])

        #HAS_SENT_MESSAGE = True
        last_update = int(time.time())
        need_to_update = True

        while True:
            ## TEST
            # if not HAS_SENT_MESSAGE:
            #     aid = Iso11783Encode(59904, 6, 6, 6)
            #     msg = can.Message(
            #         arbitration_id=aid,
            #         #data=[0x0, 0x1d, 0x1],  # DcSrcCfgBatt
            #         #data=[0x0, 0x29, 0x1],  # BattMonCfg
            #         #data=[0x0, 0x34, 0x1],  # EnDisCfg
            #         #data=[0x0, 0x65, 0x1],  # RS485Cfg
            #         #data=[0x0, 0x3A, 0x1],  # NAMECfg
            #         #data=[0x0, 0x64, 0x1],  # BattMonCfgSync 
            #         #data=[0x0, 0x25, 0x1],  # AssocCfg
            #         data=[0x14, 0xF0, 0x1], # OK - ProdInfoSts // Device Name/FGA
            #         #data=[0x10, 0xF8, 0x1], # OK - HwRevSts
            #         #data=[0xE, 0xF8, 0x1],  # OK - SwVerSts
            #         is_extended_id=True
            #     )
            #     print(msg)
            #     bus.send(msg)
            #     HAS_SENT_MESSAGE = True
            ## TEST

            message = bus.recv(1)
            (pgn, src, dst, pri) = Iso11783Decode(message.arbitration_id)

            xanbus_message = self.xanbus_queue.get(message.arbitration_id, None)
            if xanbus_message == None:
                xanbus_message = XanbusMessage(pgn,src,dst,pri)
                self.xanbus_queue[message.arbitration_id] = xanbus_message
            
            xanbus_message.append_bytes(message)
            processed_keys = []

            # If it's the first time we see the device, we send a ProdInfoSts message
            # on the Xanbus to discover what it is about
            if self.all_xanbus_devices.get(src) == None:
                aid = Iso11783Encode(59904, src, src, 6)
                msg = can.Message(
                    arbitration_id=aid,
                    data=[0x14, 0xF0, 0x1], # OK - ProdInfoSts // Device Name/FGA
                    is_extended_id=True
                )
                bus.send(msg)

                aid = Iso11783Encode(59904, src, src, 6)
                msg = can.Message(
                    arbitration_id=aid,
                    data=[0x10, 0xF8, 0x1], # OK - HwRevSts
                    is_extended_id=True
                )
                bus.send(msg)

                # We add a temporary value in our hash in order to avoid sending multiple
                # discovery messsages for the same src device
                self.all_xanbus_devices[src] = True
                continue

            for key in self.xanbus_queue.keys():
                xm = self.xanbus_queue.get(key)

                if xm.is_bogus:
                    processed_keys.append(key)
                    continue

                if xm.is_ready:
                    try:
                        self.processXanbusMessage(xm)
                    except:
                        print("Exception occured while processing Xanbus message, ingoring.")
                    processed_keys.append(key)

            for key in processed_keys:
                del self.xanbus_queue[key]

            # We publish and display our information every five seconds or so
            current_time = int(time.time())
            if current_time != last_update and (current_time-last_update) % 5 == 0:
                need_to_update = True
                last_update = current_time

            if need_to_update:
                paho_client.connect(self.config['mqtt']['host'], int(self.config['mqtt']['port']), 60)

                all_devices = {}
                for key in sorted(self.all_xanbus_devices.keys()):
                    device = self.all_xanbus_devices[key]
                    if device != True and device.serial_number != None:
                        device.publish(all_devices)
                        self.logger.info(device.formattedOutput())
                        self.logger.info("")
            
                paho_client.publish("berrybms", json.dumps(all_devices))
                paho_client.disconnect()
                need_to_update = False
                self.logger.info("Will update things in about 5 seconds...")


# When running from the command line
if __name__ == "__main__":
    f = open("config.yaml","r")
    config = yaml.load(f, Loader=yaml.SafeLoader)

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)

    xanbus_sniffer = XanbusSniffer(config, logger)
    xanbus_sniffer.sniff()