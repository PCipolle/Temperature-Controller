#!/usr/bin/python3
#-*- coding: utf-8 -*-
import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep

def read_write_room_temp():
    room_temp = 78.0
    while True:
        # tempfile = open('/sys/bus/w1/devices/28-000009b55d17/w1_slave')
        # thetext = tempfile.read()
        # tempfile.close()
        # tempdata = thetext.split("\n")[1].split(" ")[9]
        # room_temp = ((float(tempdata[2:])/1000) *1.8) + 32
        # room_temp = '{0:.1f}'.format((room_temp))

        f = open('room_temp.txt', 'a')
        f.seek(0)
        f.truncate()
        f.write(room_temp + '\n')
        f.flush()
        sleep(2)


def read_write_cond_temp():
    cond_temp = 67.0
    while True:
##        tempfile = open('/sys/bus/w1/devices/28-000009b7715e/w1_slave')
##        thetext = tempfile.read()
##        tempfile.close()
##        tempdata = thetext.split("\n")[1].split(" ")[9]
##        cond_temp = ((float(tempdata[2:])/1000) *1.8) + 32
##        cond_temp = '{0:.1f}'.format((cond_temp))
        cond_temp = cond_temp - 1.0

        f = open('cond_temp.txt', 'a')
        f.seek(0)
        f.truncate()
        f.write(str(cond_temp) + '\n')
        f.flush()
        sleep(2)


process_pool = ThreadPoolExecutor(2)
process_1 = process_pool.submit(read_write_room_temp)
process_2 = process_pool.submit(read_write_cond_temp)

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, url_for, redirect, session
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock, Event, Timer, Thread
from datetime import datetime


async_mode = None
app = Flask(__name__)
app.debug = True

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
stop_event = Event()
pool = ThreadPoolExecutor(5)

thread_1 = None
thread_2 = None
future_1 = None
future_2 = None
future_3 = None
future_4 = None
future_5 = None

condenser_heating_cycle_flag = False
compressor_cut_off_temp = 32.0
compressor_cut_in_temp = 34.0

temp_differential = 1.5

compressor_state = 0
fan_state = 0
heating_coil_state = 0
heater_1_state = 0
heater_2_state = 0

stop_event.set()

set_temperature = 75
timer_run_flag = False

room_temperature = 75
condenser_temperature = 75

def kill_all_outputs():
    global compressor_state
    global fan_state
    global heating_coil_state
    global heater_1_state
    global heater_2_state
    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0
    heater_1_state = 0
    heater_2_state = 0

def output_control():
    global condenser_temperature
    if float(set_temperature) < 75.0:
        cooling_control()
    elif float(set_temperature) >= 75.0:
        heating_control()

def cooling_control():
    global compressor_state
    global fan_state
    global heating_coil_state
    global heater_1_state
    global heater_2_state
    global condenser_temperature

    heater_1_state = 0
    heater_2_state = 0

    if float(condenser_temperature) <= compressor_cut_off_temp:
        while float(condenser_temperature) <= compressor_cut_in_temp:

            compressor_state = 0
            fan_state = 0
            heating_coil_state = 1
            socketio.emit('timeChange', {'data': 'Condenser Heating Cycle'}, broadcast=True, namespace='/test')
            eventlet.sleep(1)

    if float(room_temperature) <= (float(set_temperature) - temp_differential):

        compressor_state = 0
        fan_state = 1
        heating_coil_state = 0

    elif float(room_temperature) >= (float(set_temperature) + temp_differential):

        compressor_state = 1
        fan_state = 1
        heating_coil_state = 0

def heating_control():
    global compressor_state
    global fan_state
    global heating_coil_state
    global heater_1_state
    global heater_2_state

    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0

    if float(room_temperature) >= (float(set_temperature) + temp_differential):

        heater_1_state = 0
        heater_2_state = 0
    elif float(room_temperature) <= (float(set_temperature) - temp_differential):

        heater_1_state = 1
        heater_2_state = 1

def outputs_task():
    on = 'On'
    off = 'Off'
    while True:

        if compressor_state == 0:
            socketio.emit('compressorStateIO', {'comp': off}, namespace='/test', broadcast=True)
        else:
            socketio.emit('compressorStateIO', {'comp': on}, namespace='/test', broadcast=True)

        if fan_state == 0:
            socketio.emit('fanStateIO', {'fan': 'Off'}, namespace='/test', broadcast=True)
        else:
            socketio.emit('fanStateIO', {'fan': 'On'}, namespace='/test', broadcast=True)

        if heating_coil_state == 0:
            socketio.emit('heatCoilStateIO', {'heatCoil': 'Off'}, namespace='/test', broadcast=True)
        else:
            socketio.emit('heatCoilStateIO', {'heatCoil': 'On'}, namespace='/test', broadcast=True)

        if heater_1_state == 0:
            socketio.emit('heater1StateIO', {'heater1': 'Off'}, namespace='/test', broadcast=True)
        else:
            socketio.emit('heater1StateIO', {'heater1': 'On'}, namespace='/test', broadcast=True)

        if heater_2_state == 0:
            socketio.emit('heater2StateIO', {'heater2': 'Off'}, namespace='/test', broadcast=True)
        else:
            socketio.emit('heater2StateIO', {'heater2': 'On'}, namespace='/test', broadcast=True)

        eventlet.sleep(1)




def temp_1_task():
    global room_temperature

    while True:
        tempfile = open('room_temp.txt', 'r')
        room_temperature = tempfile.read()
        tempfile.close()
        eventlet.sleep(2)

def temp_2_task():
    global condenser_temperature

    while True:
        tempfile = open('cond_temp.txt', 'r')
        condenser_temperature = tempfile.read()
        tempfile.close()
        eventlet.sleep(2)

@app.route('/')
def tempURL():
    return redirect(url_for('temp'))

@app.route('/temperature')
def temp():
    return render_template('temperature.html')

@app.route('/IO_monitor')
def condTemp():
    return render_template('IOmonitor.html')

def update():
    return redirect(url_for('temp'))

def continuous_timer_task():
    global timer_run_flag
    timer_run_flag = True
    while (not stop_event.is_set()):
        eventlet.sleep(1)
        output_control()
        socketio.emit('timeChange', {'data': 'Running in continuous mode...'}, broadcast=True, namespace='/test')

    kill_all_outputs()
    stop_event.clear()
    timer_run_flag = False
    socketio.emit('timeChange', {'data': ""}, broadcast=True, namespace='/test')


def timer_task(setup_time):
    setup_time = setup_time * 60
    global timer_run_flag
    timer_run_flag = True
    while (not stop_event.is_set() and setup_time >= 0):

        output_control()
        hours = int(setup_time/3600)
        minutes = int(setup_time/60) % 60
        seconds = int(setup_time) % 60
        if minutes < 10:
            minutes = '0' + str(minutes)
        if seconds < 10:
            seconds = '0' + str(seconds)
        hours_minutes_seconds = str(hours) + ':' + str(minutes) + ':' + str(seconds)

        socketio.emit('timeChange', {'data': hours_minutes_seconds}, broadcast=True, namespace='/test')
        setup_time = setup_time - 1
        eventlet.sleep(1)

    kill_all_outputs()
    stop_event.clear()
    timer_run_flag = False
    socketio.emit('timeChange', {'data': ""}, broadcast=True, namespace='/test')

def temp_out_task():
    global room_temperature
    global condenser_temperature
    while True:
        eventlet.sleep(2)
        socketio.emit('currentTemp', {'temp1': room_temperature}, namespace='/test', broadcast=True)
        socketio.emit('currentTempIO', {'temp1': room_temperature}, namespace='/test', broadcast=True)
        socketio.emit('condenserTempIO', {'temp2': condenser_temperature}, namespace='/test', broadcast=True)


@socketio.on('connect_event', namespace='/test')
def connect_start():
    global timer_run_flag
    timer_run_flag = False
    global future_1
    global future_2
    global future_3
    global future_5

    socketio.emit('tempChange', {'data': set_temperature}, broadcast=True, namespace='/test')
    pool = ThreadPoolExecutor(5)
    future_1 = pool.submit(temp_1_task)
    future_2 = pool.submit(temp_2_task)
    future_3 = pool.submit(temp_out_task)
    future_5 = pool.submit(outputs_task)


@socketio.on('inc_temp_event', namespace='/test')
def increment_temp(message):
    temp = str(message['data'])
    temp = temp.strip('F')
    temp = temp.strip(u'\u00B0')
    temp = int(temp)
    if temp >= 150:
        temp = 150
    else:
        temp = temp + 5
    global set_temperature
    set_temperature = temp
    socketio.emit('tempChange', {'data': temp}, broadcast=True, namespace='/test')


@socketio.on('dec_temp_event', namespace='/test')
def decrement_temp(message):
    temp = str(message['data'])
    temp = temp.strip('F')
    temp = temp.strip(u'\u00B0')
    temp =int(temp)
    if temp <= 35:
        temp = 35
    else:
        temp = temp - 5
    global set_temperature
    set_temperature = temp
    socketio.emit('tempChange', {'data': temp}, broadcast=True, namespace='/test')


@socketio.on('start_event', namespace='/test')
def start_timer(message):
    global future_4
    global timer_run_flag
    if timer_run_flag is False:
        if future_4 != None:
            future_4.cancel()
            future_4 = None
        stop_event.clear()
        hours = (message['data1'])
        minutes = (message['data2'])
        if hours == '':
            hours = 0
        if minutes == '':
            minutes = 0

        setup_time = (int(hours) *  60) + int(minutes)
        if setup_time == 0:
            future_4 = pool.submit(continuous_timer_task)
        else:
            future_4 = pool.submit(timer_task, (setup_time))
    else:
        pass

@socketio.on('stop_event', namespace='/test')
def stop_timer():
    kill_all_outputs()
    global timer_run_flag
    timer_run_flag = False
    global future_4
    if future_4 != None:
        future_4.cancel()
        future_4 = None
        stop_event.set()


if __name__ == '__main__':
    socketio.run(app)
