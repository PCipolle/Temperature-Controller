#-*- coding: utf-8 -*-
import eventlet
eventlet.monkey_patch()
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, url_for, redirect, session
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock, Event, Timer, Thread
from datetime import datetime
from time import sleep
import atexit
from queue import Queue

async_mode = None
app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
stop_event = Event()
pool = ThreadPoolExecutor(6)

q = Queue()

future_1 = None
future_2 = None
future_3 = None
future_4 = None
future_5 = None
future_6 = None

condenser_heating_cycle_flag = False
compressor_cut_off_temp = 33.0
compressor_cut_in_temp = 36.0

temp_differential = 1.5

stop_event.set()

set_temperature = 75
timer_run_flag = False

room_temperature = 0
condenser_temperature = 0

def initialize_queue():
    print('init')
    global q
    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0
    heater_1_state = 0
    heater_2_state = 0
    q.put(compressor_state)
    q.put(fan_state)
    q.put(heating_coil_state)
    q.put(heater_1_state)
    q.put(heater_2_state)


def kill_all_outputs():
    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0
    heater_1_state = 0
    heater_2_state = 0

def output_control():
    global condenser_temperature
    condenser_temperature = condenser_temperature - 1.0
    if set_temperature < 75:
        cooling_control()
    elif set_temperature >= 75:
        heating_control()

def cooling_control():
    global q
    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0
    heater_1_state = 0
    heater_2_state = 0
    global condenser_temperature

    if condenser_temperature <= compressor_cut_off_temp:
        while condenser_temperature <= compressor_cut_in_temp:
            compressor_state = 0
            fan_state = 0
            heating_coil_state = 1
            condenser_temperature = condenser_temperature + 1
            if q.empty() == False:
                with q.mutex:
                    q.queue.clear()

            q.put(compressor_state)
            q.put(fan_state)
            q.put(heating_coil_state)
            q.put(heater_1_state)
            q.put(heater_2_state)
            socketio.emit('timeChange', {'data': 'Condenser Heating Cycle'}, broadcast=True, namespace='/test')
            eventlet.sleep(1)

    if room_temperature <= (float(set_temperature) - temp_differential):
        compressor_state = 0
        fan_state = 1

    elif room_temperature >= (float(set_temperature) + temp_differential):
        compressor_state = 1
        fan_state = 1
    if q.empty() == False:
        with q.mutex:
            q.queue.clear()

    q.put(compressor_state)
    q.put(fan_state)
    q.put(heating_coil_state)
    q.put(heater_1_state)
    q.put(heater_2_state)


def heating_control():
    global q
    compressor_state = 0
    fan_state = 0
    heating_coil_state = 0
    heater_1_state = 0
    heater_2_state = 0

    if room_temperature >= (float(set_temperature) + temp_differential):
        heater_1_state = 0
        heater_2_state = 0
    elif room_temperature <= (float(set_temperature) - temp_differential):
        heater_1_state = 1
        heater_2_state = 1

    if q.empty() == False:
        with q.mutex:
            q.queue.clear()

    q.put(compressor_state)
    q.put(fan_state)
    q.put(heating_coil_state)
    q.put(heater_1_state)
    q.put(heater_2_state)

def outputs_task():
    global q

    on = 'On'
    off = 'Off'
    while True:
        if q.empty() == True:
            pass
        else:
            compressor_state = q.get()
            fan_state = q.get()
            heating_coil_state = q.get()
            heater_1_state = q.get()
            heater_2_state = q.get()
            print(compressor_state)
            print(fan_state)
            print(heating_coil_state)
            print(heater_1_state)
            print(heater_2_state)

            q.task_done()

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
    room_temperature = 60.0
    while True:
        eventlet.sleep(2)
        #room_temperature = '{0:.2f}'.format(room_temperature)
        # tempfile1 = open('/sys/bus/w1/devices/28-000009b7715e/w1_slave')
        # thetext1 = tempfile1.read()
        # tempfile1.close()
        # tempdata1 = thetext1.split("\n")[1].split(" ")[9]
        # room_temperature = ((float(tempdata1[2:])/1000) *1.8) + 32
        # room_temperature = '{0:.2f}'.format((room_temperature))

def temp_2_task():
    global condenser_temperature
    condenser_temperature = 55.0
    while True:
        eventlet.sleep(2)
        #condenser_temperature = '{0:.2f}'.format(condenser_temperature)
        # tempfile2 = open('/sys/bus/w1/devices/28-000009b55d17/w1_slave')
        # thetext2 = tempfile2.read()
        # tempfile2.close()
        # tempdata2 = thetext2.split('\n')[1].split(" ")[9]
        # condenser_temperature = ((float(tempdata2[2:])/1000) * 1.8) + 32
        # condenser_temperature = '{0:.2f}'.format((condenser_temperature))

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

def timer_task(setup_time):
    print('starting....')
    setup_time = setup_time * 60
    global timer_run_flag
    timer_run_flag = True
    #socketio.emit('refresh', broadcast=True, namespace='/test')
    while (not stop_event.is_set() and setup_time >= 0):
        eventlet.sleep(1)
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
    if future_4 != None:
        future_4.cancel()
        future_4 = None
    global timer_run_flag
    if timer_run_flag is False:
        stop_event.clear()
        hours = int(message['data1'])
        minutes = int(message['data2'])
        setup_time = (hours *  60) + minutes
        future_4 = pool.submit(timer_task, (setup_time))
        #socketio.emit('disableStartButton', broadcast=True, namespace='/test')
    else:
        pass

@socketio.on('stop_event', namespace='/test')
def stop_timer():
    kill_all_outputs()
    global timer_run_flag
    timer_run_flag = False
    global future_4
    global future_6
    if future_4 != None:
        future_4.cancel()
        future_4 = None
        stop_event.set()


#atexit.register(kill_all_outputs)

if __name__ == '__main__':
    initialize_queue()
    socketio.run(app)
