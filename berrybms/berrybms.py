#!/usr/bin/python3
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
import sys
import time
import yaml # type: ignore
import logging
import json
import signal
import threading

import paho.mqtt.client as paho # type: ignore

from ConextAGS import ConextAGS
from ConextInsightHome import ConextInsightHome
from JKBMS import JKBMS
from JKBMSSniffer import JKBMSSniffer
from Register import Register

# Global variables to enable cleanups in signal handler
all_modbus_devices = []
paho_client = None
jkbms_sniffer = None

def cleanup(_signo, _stack_frame):
    print("Cleaning up before being terminated!")
    global paho_client
    if paho_client != None:
        paho_client.disconnect()

    global all_modbus_devices
    for device in all_modbus_devices:
        device.disconnect()
    sys.exit(0)

def main(daemon):
    # Setup the signal handler
    signal.signal(signal.SIGTERM, cleanup)

    # Load the YAML configuration file
    f = open("config.yaml","r")
    config = yaml.load(f, Loader=yaml.SafeLoader)

    while True:
        # Connect to the MQTT server. We do it each time since it's not costly
        # and avoids long keepalive if the updateinterval is set to a high value.
        global paho_client, jkbms_sniffer
        paho_client = paho.Client()
        try:
            paho_client.connect(config['mqtt']['host'], int(config['mqtt']['port']), 60)
        except:
            print("Couldn't connect to the MQTT broker, the GUI part if used, won't be updated.")
            paho_client = None

        global all_modbus_devices
        all_devices = {}
        all_bms = config.get('bms', dict())

        average_voltage = 0
        average_soc = 0
        active_bms = 0
        total_used_capacity = 0

        highest_soc = 0
        highest_id = 0
        lowest_soc = 100
        lowest_id = 0

        for key in all_bms.keys():
            bms = all_bms[key]
            bms_port = bms['port']

            if key == "jk_sniffer":
                if jkbms_sniffer == None:
                    jkbms_sniffer = JKBMSSniffer(config)
                    t = threading.Thread(target=jkbms_sniffer.sniff, daemon=True)
                    t.start()
                    print("Started JKBMS sniffer thread!")
                continue

            bms_id = bms['id']

            jkbms = JKBMS(key, bms_id, bms_port)
            c = jkbms.connect()

            if c == None:
                continue

            #print(jkbms)
            print(jkbms.formattedOutput(),'\n')

            all_modbus_devices.append(jkbms)
            active_bms += 1

            soc = jkbms.getRegister('SOCStateOfcharge').value & 0x0FF
            average_soc += soc;

            # We adjust the lowest/highest SOC
            if soc > highest_soc:
                highest_soc = soc
                highest_id = bms_id
            if lowest_soc > soc:
                lowest_soc = soc
                lowest_id = bms_id

            average_voltage += jkbms.getRegister('BatVol').value
            total_used_capacity += (jkbms.getRegister('SOCFullChargeCap').value - jkbms.getRegister('SOCCapRemain').value)

            # Publish all BMS values in MQTT
            jkbms.publish(all_devices)

        if config['insighthome'] != None:
            conext = ConextInsightHome(config['insighthome']['host'], config['insighthome']['port'], config['insighthome'].get('ids', None))
            all_modbus_devices.append(conext)
            c = conext.connect()
            devices = conext.allDevices()
            for device in devices:
                device.publish(all_devices)
                #print("%s: %s\n" % (type(device).__name__, device))
                #device.dump()
                print(device.formattedOutput(),'\n')

        # Publish all values in MQTT
        if paho_client != None:
            paho_client.publish("berrybms", json.dumps(all_devices))
            paho_client.disconnect()

        # We disconnect from all Modbus devices
        for device in all_modbus_devices:
            device.disconnect()
        all_modbus_devices = []

        if active_bms > 0:
            print("== Global BMS Statistics ==")
            average_voltage = average_voltage/active_bms
            average_soc = average_soc/active_bms

            print(f"Average Voltage:\t{average_voltage:.2f}v")
            print(f"Average SOC:\t\t{average_soc:.1f}%")
            print(f"Total Used Capacity:\t{total_used_capacity:.2f} Ah (~ {(total_used_capacity*average_voltage/1000):.2f} KWh)")
            print(f"Lowest SOC:\t\t{lowest_id} ({lowest_soc}%)  Highest: {highest_id} ({highest_soc}%)")

        if daemon:
            updateinterval = config.get('updateinterval')
            if updateinterval == None:
                updateinterval = 30
            print(f'Sleeping for {updateinterval} seconds...')
            time.sleep(updateinterval)
        else:
            break

if __name__ == "__main__":
    args = sys.argv[1:]
    daemon = False
    #print(args)
    if len(args) == 1 and args[0] == '-d':
        daemon = True

    main(daemon)
