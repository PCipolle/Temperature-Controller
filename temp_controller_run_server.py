#-*- coding: utf-8 -*-
#import os
import atexit
import eventlet
eventlet.monkey_patch()
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, url_for, redirect, session
from flask_socketio import SocketIO, emit, disconnect
from threading import Event
from datetime import datetime

async_mode = None
app = Flask(__name__)
app.debug = True

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
stop_event = Event()
stop_event.set()

thread_pool = ThreadPoolExecutor(4)

thread_1 = None
thread_2 = None
thread_3 = None

timer_run_flag = False
connect_flag = 0

def outputs_task():
    on = 'On'
    off = 'Off'
    while True:

        try:

            tempfile = open('outputs.txt', 'r')
            outputs = tempfile.readlines()
            tempfile.close()

            compressor_state = int(outputs[0])
            fan_state = int(outputs[1])
            heat_coil_state = int(outputs[2])
            heater_1_state = int(outputs[3])
            heater_2_state = int(outputs[4])

            if compressor_state == 0:
                socketio.emit('compressorStateIO', {'comp': off}, namespace='/test', broadcast=True)
            elif compressor_state == 1:
                socketio.emit('compressorStateIO', {'comp': on}, namespace='/test', broadcast=True)

            if fan_state == 0:
                socketio.emit('fanStateIO', {'fan': off}, namespace='/test', broadcast=True)
            elif fan_state == 1:
                socketio.emit('fanStateIO', {'fan': on}, namespace='/test', broadcast=True)

            if heat_coil_state == 0:
                socketio.emit('heatCoilStateIO', {'heatCoil': off}, namespace='/test', broadcast=True)
            elif heat_coil_state == 1:
                socketio.emit('heatCoilStateIO', {'heatCoil': on}, namespace='/test', broadcast=True)

            if heater_1_state == 0:
                socketio.emit('heater1StateIO', {'heater1': off}, namespace='/test', broadcast=True)
            elif heater_1_state == 1:
                socketio.emit('heater1StateIO', {'heater1': on}, namespace='/test', broadcast=True)

            if heater_2_state == 0:
                socketio.emit('heater2StateIO', {'heater2': off}, namespace='/test', broadcast=True)
            elif heater_2_state == 1:
                socketio.emit('heater2StateIO', {'heater2': on}, namespace='/test', broadcast=True)

        except:
            print('Error in outputs_task()')


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

def temp_out_task():

    while True:
        try:
            tempfile = open('room_temp.txt', 'r')
            room_temperature = tempfile.read()
            tempfile.close()
            tempfile = open('cond_temp.txt', 'r')
            condenser_temperature = tempfile.read()
            tempfile.close()

            eventlet.sleep(2)
            socketio.emit('currentTemp', {'temp1': room_temperature}, namespace='/test', broadcast=True)
            socketio.emit('currentTempIO', {'temp1': room_temperature}, namespace='/test', broadcast=True)
            socketio.emit('condenserTempIO', {'temp2': condenser_temperature}, namespace='/test', broadcast=True)

        except:
            print('Error in temp_out_task()')

@socketio.on('inc_temp_event', namespace='/test')
def increment_temp(message):
    try:
        temp = str(message['data'])
        temp = temp.strip('F')
        temp = temp.strip(u'\u00B0')
        temp = int(temp)
        if temp >= 160:
            temp = 160
        else:
            temp = temp + 5
            f = open('set_temp.txt', 'a')
            f.seek(0)
            f.truncate()
            f.write(str(temp) + '\n')
            f.flush()
            f.close()
        socketio.emit('tempChange', {'data': temp}, broadcast=True, namespace='/test')

    except:
        print('Error in increment_temp()')

@socketio.on('dec_temp_event', namespace='/test')
def decrement_temp(message):
    try:
        temp = str(message['data'])
        temp = temp.strip('F')
        temp = temp.strip(u'\u00B0')
        temp =int(temp)
        if temp <= 35:
            temp = 35
        else:
            temp = temp - 5
        f = open('set_temp.txt', 'a')
        f.seek(0)
        f.truncate()
        f.write(str(temp) + '\n')
        f.flush()
        f.close()
        socketio.emit('tempChange', {'data': temp}, broadcast=True, namespace='/test')

    except:
        print('Error in decrement_temp()')

def continuous_timer_task():

    global timer_run_flag
    timer_run_flag = True
    while (not stop_event.is_set()):
        eventlet.sleep(1)
        try:
            socketio.emit('timeChange', {'data': 'Running in continuous mode...'}, broadcast=True, namespace='/test')
        except:
            print('Error in continuous_timer_task()')


    run_flag = 0
    f = open('run_flag.txt', 'a')
    f.seek(0)
    f.truncate()
    f.write(str(run_flag))
    f.flush()
    f.close()
    stop_event.clear()
    timer_run_flag = False
    socketio.emit('timeChange', {'data': ""}, broadcast=True, namespace='/test')

def timer_task(setup_time):
    global thread_2
    global timer_run_flag
    setup_time = setup_time * 60

    timer_run_flag = True
    while (not stop_event.is_set() and setup_time > 0):
        try:
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

        except:
            print('Error in timer_task()')

        eventlet.sleep(1)

    run_flag = 0
    f = open('run_flag.txt', 'a')
    f.seek(0)
    f.truncate()
    f.write(str(run_flag))
    f.flush()
    f.close()
    #thread_2 = thread_pool.submit(timer_task, (setup_time))
    stop_event.clear()
    timer_run_flag = False
    socketio.emit('timeChange', {'data': ""}, broadcast=True, namespace='/test')


@socketio.on('start_event', namespace='/test')
def start_timer(message):
    global thread_2
    global timer_run_flag
    try:

        if timer_run_flag == False:
            if thread_2 != None:
                thread_2.cancel()
                thread_2 = None
            stop_event.clear()

            hours = (message['data1'])
            minutes = (message['data2'])
            if hours == '':
                hours = 0
            if minutes == '':
                minutes = 0

            setup_time = (int(hours) *  60) + int(minutes)
            if setup_time == 0:
                run_flag = 1
                f = open('run_flag.txt', 'a')
                f.seek(0)
                f.truncate()
                f.write(str(run_flag))
                f.flush()
                f.close()
                thread_2 = thread_pool.submit(continuous_timer_task)
            else:
                run_flag = 1
                f = open('run_flag.txt', 'a')
                f.seek(0)
                f.truncate()
                f.write(str(run_flag))
                f.flush()
                f.close()
                thread_2 = thread_pool.submit(timer_task, (setup_time))

        else:
            pass

    except:
        print('Error in start_timer()')

@socketio.on('stop_event', namespace='/test')
def stop_timer():
    global thread_2
    global timer_run_flag
    try:

        timer_run_flag = False

        run_flag = 0
        f = open('run_flag.txt', 'a')
        f.seek(0)
        f.truncate()
        f.write(str(run_flag))
        f.flush()
        f.close()
        if thread_2 != None:
            thread_2.cancel()
            thread_2 = None
            stop_event.set()

    except:
        print('Error in stop_timer()')

def clear_run_flag():
    run_flag = 0
    f = open('run_flag.txt', 'a')
    f.seek(0)
    f.truncate()
    f.write(str(run_flag))
    f.flush()
    f.close()

def timed_start():
    count = 0
    global thread_2
    while count <= 720:
        print(datetime.now())
        eventlet.sleep(60)
        count = count + 1

    try:

        global timer_run_flag
        if timer_run_flag == False:
            if thread_2 != None:
                thread_2.cancel()
                thread_2 = None
            stop_event.clear()

            hours = 0
            minutes = 0
            if hours == '':
                hours = 0
            if minutes == '':
                minutes = 0

            setup_time = (int(hours) *  60) + int(minutes)
            if setup_time == 0:
                run_flag = 1
                f = open('run_flag.txt', 'a')
                f.seek(0)
                f.truncate()
                f.write(str(run_flag))
                f.flush()
                f.close()
                thread_2 = thread_pool.submit(continuous_timer_task)
            else:
                run_flag = 1
                f = open('run_flag.txt', 'a')
                f.seek(0)
                f.truncate()
                f.write(str(run_flag))
                f.flush()
                f.close()
                thread_2 = thread_pool.submit(timer_task, (setup_time))

        else:
            pass

    except:
        print('Error in start_timer()')


@socketio.on('connect_event', namespace='/test')
def connect_start():

    try:

        tempfile = open('set_temp.txt', 'r')
        set_temperature = tempfile.read()
        tempfile.close()
        socketio.emit('tempChange', {'data': set_temperature}, broadcast=True, namespace='/test')

    except:
        print('Error in connect_start()')

def cleanup_routine():
    clear_run_flag()

if __name__ == '__main__':
    clear_run_flag()
    thread_1 = thread_pool.submit(temp_out_task)
    thread_3 = thread_pool.submit(outputs_task)
    socketio.run(app)
    atexit.register(cleanup_routine)




    #thread_4 = thread_pool.submit(timed_start)
