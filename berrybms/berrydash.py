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
import dash
from dash import Dash, html, dcc, Input, Output
import dash_daq as daq
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import plotly.graph_objects as go
import time
import sys
from flask_mqtt import Mqtt
import json

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME])
server = app.server
load_figure_template("darkly")

server.config['MQTT_BROKER_URL'] = 'localhost'
server.config['MQTT_BROKER_PORT'] = 1883 
mqtt = Mqtt()
mqtt.init_app(app)

all_battmon = {}
all_bms = {}
all_mppt = {}
all_xw = {}

@mqtt.on_connect()
def handle_connect(client, userdata, flags, reason_code):
    print("Connected with result code "+ str(reason_code))
    mqtt.subscribe("berrybms")

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
     devices = json.loads(message.payload)
     #print("Got values (%s) from MQTT from topic: %s" % (str(devices), message.topic))
     for key in devices.keys():
        if key.startswith("battmon"):
            global all_battmon
            all_battmon[key] = devices[key]
        elif key.startswith("bms"):
            global all_bms
            all_bms[key] = devices[key]
        elif key.startswith("mppt"):
            global all_mppt
            all_mppt[key] = devices[key]
        elif key.startswith("xw"):
            global all_xw
            all_xw[key] = devices[key]

def buildConextGauge():
    if len(all_xw) == 0:
        return None
    
    active_power = 0
    #battery_power = 0
    ac_load_active_power = 0
    mppt_dc_output_power = 0
    pv_input_active_today = 0
    grid_ac_input_power = 0
    grid_active_today = 0
    generator_ac_power = 0
    generator_active_today = 0
    charge_dc_power = 0
    charge_dc_current = 0

    for key in all_xw.keys():
        xw = all_xw[key]
        #battery_power += xw['BatteryPower']
        ac_load_active_power += xw['LoadACPowerApparent']
        grid_ac_input_power += xw['GridACInputPower']
        grid_active_today += xw['GridInputActiveToday']
        generator_ac_power += xw['GeneratorACPowerApparent']
        generator_active_today += xw['GeneratorInputActiveToday']
        charge_dc_power += xw['ChargeDCPower']
        charge_dc_current += xw['ChargeDCCurrent']

    for key in all_mppt.keys():
            mppt = all_mppt[key]
            mppt_dc_output_power += mppt['DCOutputPower']
            pv_input_active_today += mppt['PVInputActiveToday']

    active_power =(mppt_dc_output_power+grid_ac_input_power+generator_ac_power)-(ac_load_active_power)

    gauge = daq.Gauge(
        showCurrentValue=True,
        color={"gradient": True, "ranges": {"red": [-10000, -1000], "yellow": [-1000, 1000], "green": [1000, 10000]}},
        id="active-power-gauge",
        max=10000,
        min=-10000,
        size=200,
        units="Watts",
        style={'display': 'block', 'margin-bottom': -80, 'margin-top': -15}, 
        value=active_power,
        digits=0   # available after 0.5, see https://github.com/plotly/dash-daq/pull/117/files
    )

    row1 = html.Tr([html.Td("AC Load Active"), html.Td(f'{ac_load_active_power} W')])
    row2 = html.Tr([html.Td("MPPT DC Ouput"),
                    html.Td(['{} W ({} '.format(mppt_dc_output_power, time.strftime("%H:%M:%S", time.gmtime(pv_input_active_today))),
                            html.I(className='fa-solid fa-hourglass'),
                            ')'])
                    ])
    row3 = html.Tr([html.Td("Grid AC Input"),
                    html.Td(['{} W ({} '.format(grid_ac_input_power, time.strftime("%H:%M:%S", time.gmtime(grid_active_today))),
                            html.I(className='fa-solid fa-hourglass'),
                            ')'])
                    ])
    row4 = html.Tr([html.Td("Generator AC Input"),
                    html.Td(['{} W ({} '.format(generator_ac_power, time.strftime("%H:%M:%S", time.gmtime(generator_active_today))),
                            html.I(className='fa-solid fa-hourglass'),
                            ')'])
                    ])
    row5 = html.Tr([html.Td("XW+ Charge DC"), html.Td(f'{charge_dc_power} W ({charge_dc_current:.2f} A)')])
    table_body_left = [html.Tbody([row1, row2, row3, row4, row5])]

    card = dbc.Card(
        [
            dbc.CardHeader(children=[html.B("Active Power", style={'font-size':'13px'})]),
            dbc.CardBody([
                gauge,
                dbc.Table(table_body_left, dark=True, striped=True, bordered=False, hover=True, style={'font-size': '11px'})
            ], style={
                    'padding': '0'
            })    
        ],
        #color="primary",
        inverse=True,
        style={"width": "16rem"}
    )

    return card

def buildConextStats():
    if len(all_bms) == 0 or len(all_battmon) == 0:
        return None

    average_bms_soc = 0
    lowest_bms_soc = 100
    highest_bms_soc = 0
    average_battmon_soc = 0
    average_bms_voltage = 0
    average_bms_current = 0
    average_battmon_voltage = 0
    average_battmon_current = 0
    removed_bms_capacity = 0
    remaining_bms_capacity = 0
    total_bms_capacity = 0
    removed_battmon_capacity = 0
    remaining_battmon_capacity = 0
    total_battmon_capacity = 0
    average_mppt_efficiency = 0
    total_producing_mppt = 0

    for key in all_bms.keys():
        bms = all_bms[key]
        soc = (bms['SOCStateOfcharge'] & 0x0FF)
        if soc > highest_bms_soc:
            highest_bms_soc = soc
        if lowest_bms_soc > soc:
            lowest_bms_soc = soc
        average_bms_soc += soc
        average_bms_voltage += bms['BatVol']
        average_bms_current += bms['BatCurrent']
        remaining_bms_capacity += bms['SOCCapRemain']
        total_bms_capacity += bms['SOCFullChargeCap']
    average_bms_soc /= len(all_bms)
    average_bms_voltage /= len(all_bms)
    removed_bms_capacity = total_bms_capacity-remaining_bms_capacity

    if len(all_battmon):
        for key in all_battmon.keys():
            battmon = all_battmon[key]
            average_battmon_soc += battmon['BatterySOC']
            average_battmon_voltage += battmon['BatteryVoltage']
            average_battmon_current += battmon['BatteryCurrent']
            remaining_battmon_capacity += battmon['BatteryCapacityRemaining']
            removed_battmon_capacity += battmon['BatteryCapacityRemoved']
            total_battmon_capacity += battmon['BatteryCapacity']
        average_battmon_soc /=  len(all_battmon)
        average_battmon_voltage /= len(all_battmon)

    if (len(all_mppt)):
        for key in all_mppt.keys():
            mppt = all_mppt[key]
            if mppt['DCOutputPower'] > 0 and mppt['PVPower'] > 0:
                average_mppt_efficiency += mppt['DCOutputPower']/mppt['PVPower']
                total_producing_mppt += 1
        if total_producing_mppt > 0:
           average_mppt_efficiency /= total_producing_mppt
    
    row1 = html.Tr([html.Td("Average SOC (BMS)"), html.Td(f'{average_bms_soc:.2f} % ({lowest_bms_soc} % / {highest_bms_soc} %)')])
    row2 = html.Tr([html.Td("Average SOC (BattMon)"), html.Td(f'{average_battmon_soc:.2f} %')])
    row3 = html.Tr([html.Td("Average voltage/current (BMS)"), html.Td(f'{average_bms_voltage:.2f} v / {average_bms_current:.2f} A')])
    row4 = html.Tr([html.Td("Average voltage/current (BattMon)"), html.Td(f'{average_battmon_voltage:.2f} v / {average_battmon_current:.2f} A')])
    row5 = html.Tr([html.Td("Removed capacity (BMS)"), html.Td(f'{removed_bms_capacity:.1f} Ah ({remaining_bms_capacity:.1f} Ah remaining of {total_bms_capacity:.0f} Ah)')])
    row6 = html.Tr([html.Td("Removed capacity (BattMon)"), html.Td(f'{removed_battmon_capacity:.1f} Ah ({remaining_battmon_capacity:.1f} Ah remaining of {total_battmon_capacity:.0f} Ah)')])
    row7 = html.Tr([html.Td("Average MPPT efficiency"), html.Td(f'{average_mppt_efficiency*100:.0f} %')])
    table_body_right = [html.Tbody([row1, row2, row3, row4, row5, row6, row7])]

    table = dbc.Table(table_body_right, dark=True, striped=True, bordered=False, hover=True, responsive=True, style={'font-size': '11px'})

    card = dbc.Card(
        [
            dbc.CardHeader(children=[html.B("BMS/Conext Statistics", style={'font-size':'13px'})]),
            dbc.CardBody([
                table
            ], style={
                    'padding': '0'
            })    
        ],
        style={"width": "16rem", "height": "100%"}
    )

    return card

def buildBMSGauge(key, bms):
    cellCount = bms.get("CellCount")
    highestCellVoltage = 0
    lowestCellVoltage = sys.maxsize
    highestCellIndex = 0
    lowestCellIndex = 0
    cellVoltageDrift = 0
    badges = []
    tooltips = []

    for i in range(0,cellCount):
        cellVoltage = round(float(bms.get(f'CellVol{i}')),3)
        if cellVoltage < lowestCellVoltage:
            lowestCellIndex = i
            lowestCellVoltage = cellVoltage
        elif cellVoltage >= highestCellVoltage:
            highestCellIndex = i
            highestCellVoltage = cellVoltage
        b = dbc.Badge(f'{cellVoltage:.3f}v', color="primary", id=f'{key}-cellVol{i}')
        badges.append(b)
        tooltips.append(dbc.Tooltip(f'Cell {i+1}', target=f'{key}-cellVol{i}'))

    badges[highestCellIndex].color = "green"
    badges[lowestCellIndex].color = "warning"
    cellVoltageDrift = highestCellVoltage-lowestCellVoltage

    warning_icon_color = 'gray'
    warning_message = 'No warning'
    if bms.get("Alarms") > 0:
        warning_icon_color = 'red'

    if bms['BatCurrent'] > 0:
        charge_discharge_icon = 'fa-solid fa-plus'
        charge_discharge_icon_color = 'green'
    else:
        charge_discharge_icon = 'fa-solid fa-minus'
        charge_discharge_icon_color = 'red'

    card = dbc.Card(
        [
            dbc.CardHeader(children=[
                html.B(f"{bms['name']} - {bms['ManufacturerDeviceID']} (v{bms['SoftwareVersion']}) ", style={'font-size':'13px'}),
                html.I(className='fa-solid fa-triangle-exclamation', style={"color": warning_icon_color}, id=f'{key}-warning'),
                dbc.Tooltip(warning_message, target=f'{key}-warning')
                ]),    
            dbc.CardBody([
                daq.Gauge(
                    showCurrentValue=True,
                    color={"gradient": True, "ranges": {"red": [0, 25], "yellow": [25, 65], "green": [65, 100]}},
                    labelPosition='top',
                    id=f'soc-gauge-{key}',
                    max=100,
                    size=200,
                    units=f"{bms['SOCCapRemain']:.2f} Ah of {bms['SOCFullChargeCap']:.0f}",
                    style={'display': 'block', 'margin-bottom': -80, 'margin-top': -30}, 
                    value=bms['SOCStateOfcharge'],
                    digits=0   # available after 0.5, see https://github.com/plotly/dash-daq/pull/117/files
                ),
                html.Span([
                        html.I(className=charge_discharge_icon, style={"color": charge_discharge_icon_color}),
                        html.Span(f" {abs(bms['BatCurrent']):.2f}A/{(abs(bms['BatCurrent'])*bms['BatVol']):.0f}W ({bms['SOCCycleCount']} cycles, {cellVoltageDrift:.3f}v drift)")
                ], style={'font-size':'13px'}),
                html.Br(),
                html.Span(badges+tooltips)
            ])    
        ],
        #color="primary",
        inverse=True,
        style={"width": "16rem", 'padding': '0'}
    )

    return card

def buildBMSGauges():
    cols = []
    for key in all_bms.keys():
        bms = all_bms[key]
        card = buildBMSGauge(key, bms)
        cols.append(dbc.Col(card))
    
    return dbc.Row(id='bms-gauges', children=cols, className="g-0")

app.layout = html.Div([
        dcc.Interval(
            id='interval-component',
            interval=5*1000,
            n_intervals=0
        ),
        html.Div(dbc.Row([
                        dbc.Col(id='conext-gauge', children=[buildConextGauge()]),
                        dbc.Col(id='conext-stats', children=[buildConextStats()]),
                        dbc.Col(dbc.Tabs(id='tabs', active_tab='tab-0'))
                        ],
                className="g-0")),
        html.Div(buildBMSGauges())
    ])

@app.callback(Output(component_id='conext-gauge', component_property='children'),
              Input(component_id='interval-component', component_property='n_intervals'))
def update_conext_gauge(n):
    return buildConextGauge()

@app.callback(Output(component_id='conext-stats', component_property='children'),
              Input(component_id='interval-component', component_property='n_intervals'))
def update_conext_stats(n):
    return buildConextStats()

@app.callback(Output(component_id='bms-gauges', component_property='children'),
              Input(component_id='interval-component', component_property='n_intervals'))
def update_bms_gauges(n):
    return buildBMSGauges()

@app.callback(Output(component_id='tabs', component_property='children'),
              Input(component_id='interval-component', component_property='n_intervals'))
def update_tabs(n):
    tabs = []
    if len(all_mppt) == 0:
        return None
    
    x_axis = ['Battery Out', 'Battery In', 'PV In', 'Generator In', 'Grid In', 'Load Out']
    tab_index = 0
    for period in ['ThisHour', 'Today', 'ThisWeek', 'ThisMonth']:
        y_axis = [0, 0, 0, 0, 0, 0]

        # Get data from the MPPT charge controllers
        for key in all_mppt.keys():
            mppt = all_mppt[key]
            y_axis[1] += mppt[f'EnergyToBattery{period}']
            y_axis[2] += mppt[f'EnergyFromPV{period}']

        # Get data from the XW inverters
        for key in all_xw.keys():
            xw = all_xw[key]
            y_axis[0] += xw[f'EnergyToBattery{period}']
            y_axis[1] += xw[f'EnergyFromBattery{period}']
            y_axis[3] += xw[f'GeneratorInputEnergy{period}']
            y_axis[4] += xw[f'GridInputEnergy{period}']
            y_axis[5] += xw[f'LoadOutputEnergy{period}']

        for i in range(0,6):
            y_axis[i] = round(y_axis[i], 2)

        colors = ['crimson','aqua','aquamarine','aquamarine','aquamarine','crimson']
        fig = go.Figure(data=[go.Bar(
                    x=x_axis,
                    y=y_axis,
                    text=y_axis,
                    textposition='auto',
                    marker_color=colors
                    )]
        )
        fig.update_layout(margin=dict(l=5, r=5, t=5, b=5))
        fig.update_yaxes(title='kWh')

        tab = dbc.Tab(id=f'tab-{tab_index}',
                      label=period.replace('This',''),
                      active_label_style={"color": "#F39C12"},
                      children=[dcc.Graph(id=f'graph-{period}', figure=fig, config={'displayModeBar': False}, style={'width': '50vw', 'height': '45vh'})]
                    )
        tabs.append(tab)
        tab_index += 1
    
    return tabs

if __name__ == '__main__':
    app.run_server(debug=False, port=8080, host='0.0.0.0', use_reloader=False)