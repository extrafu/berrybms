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
import struct
import binascii
import serial # type: ignore
import logging
import sys

import paho.mqtt.client as paho # type: ignore
import json
import yaml # type: ignore

from JKBMS import JKBMS

class JKBMSSniffer(object):

    STATUS_COMMAND = bytearray([0x10,0x16,0x20,0x00,0x01,0x02,0x00,0x00])
    SETTINGS_COMMAND = bytearray([0x10,0x16,0x1E,0x00,0x01,0x02,0x00,0x00])
    ABOUT_COMMAND = bytearray([0x10,0x16,0x1C,0x00,0x01,0x02,0x00,0x00])
    RESPONSE_HEADER = bytearray([0x55,0xAA,0xEB,0x90])

    def __init__(self,
                 config,
                 logger):
          
            self.config = config
            self.logger = logger
            self.s_con = self.setup_serial(config)
            self.all_bms = [None] * 16
            self.read_buffer = bytearray()
    
    def setup_serial(self, config):
        s_con = serial.Serial(config['bms']['jk_sniffer']['port'])
        s_con.baudrate = 115200
        s_con.bytesize = serial.EIGHTBITS
        s_con.stopbits = serial.STOPBITS_ONE
        s_con.parity = serial.PARITY_NONE
        return s_con

    def decode_about(self, bytes, bms_id):
        #print(f'decoding about from bytes: {binascii.hexlify(bytes)} len={len(bytes)}')
        bms = self.all_bms[bms_id]
        if bms is not None:
            bms.values["ManufacturerDeviceID"] = bytes[0:15].decode("UTF-8")
            bms.values["HardwareVersion"] = bytes[16:23].decode("UTF-8")
            bms.values["SoftwareVersion"] = bytes[24:31].decode("UTF-8")
            self.logger.info(bms.formattedOutput())
            self.logger.info("")

    def decode_status(self, bytes, bms_id):
        #print(f'decoding status from bytes: {binascii.hexlify(bytes)} len={len(bytes)}')        
        voltages = list(map(lambda x: x/1000, struct.unpack("<32H", bytes[:64])))
        #print(f'Cell voltages (v): {voltages}')
        
        (CellVolAve,) = struct.unpack("<H", bytes[68:70])
        #print(f'CellVolAve={CellVolAve[0]/1000}')

        #resistances = list(map(lambda x: x/1000, struct.unpack("<32H", bytes[74:138])))
        #print(f'Cell resistances (ohm): {resistances}')

        (BatVol,BatWatt,BatCurrent,Alarm) = struct.unpack("<IIixxxxI", bytes[144:164])
        #print(f'BatVol={BatVol/1000} BatWatt={BatWatt/1000} BatCurrent={BatCurrent/1000} Alarm={Alarm}')

        (BalanSta,SOCStateOfcharge,SOCCapRemain,SOCFullChargeCap,SOCCycleCount) = struct.unpack("<BBiII", bytes[166:180])

        bms = self.all_bms[bms_id]
        if bms is not None:
            for i in range(32):
                voltage = voltages[i]
                if voltage == 0:
                    break
                bms.values[f'CellVol{i}'] = voltage

            bms.values.update({
                "CellVolAve": CellVolAve / 1000,
                "BatVol": BatVol / 1000,
                "BatWatt": BatWatt / 1000,
                "BatCurrent": BatCurrent / 1000,
                "Alarm": Alarm,
                "BalanSta": BalanSta,
                "SOCStateOfcharge": SOCStateOfcharge,
                "SOCCapRemain": SOCCapRemain / 1000,
                "SOCFullChargeCap": SOCFullChargeCap / 1000,
                "SOCCycleCount": SOCCycleCount,
            })
            self.logger.info(bms.formattedOutput())
            self.logger.info("")

    def decode_settings(self, bytes, bms_id):
        #print(f'decoding settings from bytes: {binascii.hexlify(bytes)} len={len(bytes)}')
        bms = self.all_bms[bms_id]
        if bms is not None:
            (bms.values["CellCount"],bms.values["BatChargeEN"],bms.values["BatDisChargeEN"]) = struct.unpack("<III", bytes[108:120])
            self.logger.info(bms.formattedOutput())
            self.logger.info("")

    def read_from_bms(self):        
        l = len(self.read_buffer)
        
        # Our read_buffer is big enough, let's try to find our response header
        if l >= 308:
            for i in range(l):
                if i+308 < l and self.read_buffer[i:i+4] == JKBMSSniffer.RESPONSE_HEADER:
                    response = self.read_buffer[i:i+308]
                    # We discard everything before the header. This will generally be the commands
                    # sent by the MASTER BMS to all slaves. We aren't interested in those for now.
                    self.read_buffer = self.read_buffer[i+308:]

                    computed_checkum = self.chksum(response, 299)
                    checksum = int.from_bytes(response[299:300])
                    #print(f'computed_checksum={computed_checkum} checksum={checksum}')
                    if computed_checkum == checksum:
                        return response

                    #print(f'Invalid packet, skipping! {binascii.hexlify(response)}')
                    return None

        # Buffer not big enough, let's continue to accumulate bytes
        #print(f'remaining read_buffer length: {len(self.read_buffer)} read_buffer={binascii.hexlify(self.read_buffer)}')
        available = self.s_con.inWaiting()
        self.read_buffer += self.s_con.read(available)
        return None

    def force_data_discovery(self):
        for i in reversed(range(16)):
            bms = self.all_bms[i]
            if bms == None:
                continue

            command = bytearray([i])

            # We try to be smart here. We want SETTINGS and STATUS information first, then ABOUT information
            if bms.values.get("CellCount") == None:
                command += JKBMSSniffer.SETTINGS_COMMAND
            elif bms.values.get("SOCStateOfcharge") == None:
                command += JKBMSSniffer.STATUS_COMMAND
            # The master BMS never answers the ABOUT command. We send it anyway in case JK eventually
            # decides to fix the issue.
            elif bms.values.get("ManufacturerDeviceID") == None:
                command += JKBMSSniffer.ABOUT_COMMAND

            if len(command) > 1:
                #print(f'Forcing data discovery for bms {i}')
                crc = self.modbus_crc(command)
                #print(f'crc={crc}')
                command += crc
                self.s_con.write(command)
                #print(f'command sent! {binascii.hexlify(command)}')
                return

    # Copied from https://stackoverflow.com/a/75328573 to calculate the needed checksum
    def modbus_crc(self, msg):
        crc = 0xFFFF
        for n in range(len(msg)):
            crc ^= msg[n]
            for i in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, "little")

    def chksum(self, bytes, len):
        checksum = sum(bytes[0:len])
        return (checksum & 0xFF)

    def sniff(self):
        paho_client = paho.Client()
        response_count = 1

        while True:
            response = self.read_from_bms()

            if response != None:
                frame_type = int.from_bytes(response[4:5])
                if frame_type == 0x1:
                    bms_id = int.from_bytes(response[270:271])
                else:
                    bms_id = int.from_bytes(response[300:301])

                # We sometimes get broken BMS identifier, so we skip the whole thing
                # if it happens.
                if bms_id > 16:
                    continue

                #print(f'response={binascii.hexlify(response)} len={len(response)}')        
                #print(f'frame_type={frame_type} bms_id={bms_id}')

                # We check if we need to initialize an empty BMS
                bms = self.all_bms[bms_id]
                if bms == None:
                    name = f'jk{bms_id}' # TODO: be more flexible here
                    bms = JKBMS(name, bms_id)
                    self.all_bms[bms_id] = bms

                match frame_type:
                    case 0x1:
                        self.decode_settings(response[6:], bms_id)
                        pass
                    case 0x2:
                        self.decode_status(response[6:], bms_id)
                        pass
                    case 0x3:
                        self.decode_about(response[6:], bms_id)
                    case _:
                        print("Unknown reponse! %s" % (binascii.hexlify(response)))
                        #exit(1)

                # Publish the updates to MQTT
                self.publish_updates(paho_client, bms)

                # We force the discovery of other data. The "about" data
                # seems to never be advertised without asking for it.
                if response_count % 10 == 0:
                    self.force_data_discovery()
                response_count += 1

    def publish_updates(self, paho_client, bms):
        paho_client.connect(self.config['mqtt']['host'], int(self.config['mqtt']['port']), 60)
        all_devices = {}
        bms.publish(all_devices)
        paho_client.publish("berrybms", json.dumps(all_devices))
        paho_client.disconnect()


# When running from the command line
if __name__ == "__main__":
    f = open("config.yaml","r")
    config = yaml.load(f, Loader=yaml.SafeLoader)

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)

    jkbms_sniffer = JKBMSSniffer(config, logger)
    jkbms_sniffer.sniff()