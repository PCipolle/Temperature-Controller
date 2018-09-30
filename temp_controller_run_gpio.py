#-*- coding: utf-8 -*-
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from datetime import datetime
import atexit
import RPi.GPIO as GPIO

COMPRESSOR_PIN = 11
FAN_PIN = 13
HEAT_COIL_PIN = 15
HEATER_1_PIN = 29
HEATER_2_PIN = 31

GPIO.setmode(GPIO.BOARD)
GPIO.setup(COMPRESSOR_PIN, GPIO.OUT)
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.setup(HEAT_COIL_PIN, GPIO.OUT)
GPIO.setup(HEATER_1_PIN, GPIO.OUT)
GPIO.setup(HEATER_2_PIN, GPIO.OUT)


COMPRESSOR_CUT_OFF_TEMP = 31.0
COMPRESSOR_CUT_IN_TEMP = 33.0

HEAT_TEMP_LOW = 0.5
HEAT_TEMP_HIGH = 1.5

COOL_TEMP_LOW = 1.5
COOL_TEMP_HIGH = 0.5

process_pool = ProcessPoolExecutor(1)
thread_pool = ThreadPoolExecutor(2)

def init_outputs():
    GPIO.output(COMPRESSOR_PIN, False)
    GPIO.output(FAN_PIN, False)
    GPIO.output(HEAT_COIL_PIN, False)
    GPIO.output(HEATER_1_PIN, False)
    GPIO.output(HEATER_2_PIN, False)

init_outputs()

def write_gpio_status():
    try:
        compressor_state = GPIO.input(COMPRESSOR_PIN)
        fan_state = GPIO.input(FAN_PIN)
        heat_coil_state = GPIO.input(HEAT_COIL_PIN)
        heater_1_state = GPIO.input(HEATER_1_PIN)
        heater_2_state = GPIO.input(HEATER_2_PIN)
        f = open('outputs.txt', 'a')
        f.seek(0)
        f.truncate()
        f.write(str(compressor_state) + '\n')
        f.write(str(fan_state) + '\n')
        f.write(str(heat_coil_state) + '\n')
        f.write(str(heater_1_state) + '\n')
        f.write(str(heater_2_state) + '\n')
        f.flush()
        f.close()

    except:
        print('Error in write_gpio_status()')

write_gpio_status()

def read_write_temps():

    while True:
        try:
            tempfile = open('/sys/bus/w1/devices/28-000009b55d17/w1_slave')
            thetext = tempfile.read()
            tempfile.close()
            tempdata = thetext.split("\n")[1].split(" ")[9]
            room_temp = ((float(tempdata[2:])/1000) *1.8) + 32
            room_temp = '{0:.1f}'.format((room_temp))
            f = open('room_temp.txt', 'a')
            f.seek(0)
            f.truncate()
            f.write(str(room_temp) + '\n')
            f.flush()
            f.close()

            tempfile = open('/sys/bus/w1/devices/28-000009b7715e/w1_slave')
            thetext = tempfile.read()
            tempfile.close()
            tempdata = thetext.split("\n")[1].split(" ")[9]
            cond_temp = ((float(tempdata[2:])/1000) *1.8) + 32
            cond_temp = '{0:.1f}'.format((cond_temp))
            f = open('cond_temp.txt', 'a')
            f.seek(0)
            f.truncate()
            f.write(str(cond_temp) + '\n')
            f.flush()
            f.close()

        except:
            print('Error in read_write_temps()')

        sleep(2)






def kill_all_outputs():

    GPIO.output(COMPRESSOR_PIN, False)
    GPIO.output(FAN_PIN, False)
    GPIO.output(HEAT_COIL_PIN, False)
    GPIO.output(HEATER_1_PIN, False)
    GPIO.output(HEATER_2_PIN, False)

def gpio_cooling_control(set_temperature, room_temperature, condenser_temperature):
    GPIO.output(HEATER_1_PIN, False)
    GPIO.output(HEATER_2_PIN, False)
    if float(condenser_temperature) <= COMPRESSOR_CUT_OFF_TEMP:
        while float(condenser_temperature) <= COMPRESSOR_CUT_IN_TEMP:
            try:
                tempfile = open('cond_temp.txt', 'r')
                condenser_temperature = tempfile.read()
                tempfile.close()
                GPIO.output(COMPRESSOR_PIN, False)
                GPIO.output(FAN_PIN, False)
                GPIO.output(HEAT_COIL_PIN, True)
            except:
                print('Error in condenser heater loop()')

            sleep(1)

    if float(room_temperature) <= (float(set_temperature) - COOL_TEMP_LOW):
        GPIO.output(COMPRESSOR_PIN, False)
        GPIO.output(FAN_PIN, True)
        GPIO.output(HEAT_COIL_PIN, False)


    elif float(room_temperature) >= (float(set_temperature) + COOL_TEMP_HIGH):
        GPIO.output(COMPRESSOR_PIN, True)
        GPIO.output(FAN_PIN, True)
        GPIO.output(HEAT_COIL_PIN, False)



def gpio_heating_control(set_temperature, room_temperature, condenser_temperature):

    GPIO.output(COMPRESSOR_PIN, False)
    GPIO.output(FAN_PIN, False)
    GPIO.output(HEAT_COIL_PIN, False)

    if float(room_temperature) >= (float(set_temperature) + HEAT_TEMP_HIGH):
        GPIO.output(HEATER_1_PIN, False)
        GPIO.output(HEATER_2_PIN, False)

    elif float(room_temperature) <= (float(set_temperature) - HEAT_TEMP_LOW):
        GPIO.output(HEATER_1_PIN, True)
        GPIO.output(HEATER_2_PIN, True)



def gpio_output_control():

    while True:

        try:
            tempfile = open('run_flag.txt', 'r')
            run_flag = tempfile.read()
            tempfile.close()
            if int(run_flag) == 1:

                tempfile = open('set_temp.txt', 'r')
                set_temperature = tempfile.read()
                tempfile.close()

                tempfile = open('room_temp.txt', 'r')
                room_temperature = tempfile.read()
                tempfile.close()

                tempfile = open('cond_temp.txt', 'r')
                condenser_temperature = tempfile.read()
                tempfile.close()

                if float(set_temperature) < 75.0:
                    gpio_cooling_control(set_temperature, room_temperature, condenser_temperature)
                elif float(set_temperature) >= 75.0:
                    gpio_heating_control(set_temperature, room_temperature, condenser_temperature)

            else:
                kill_all_outputs()

        except:
            print('Error in gpio_output_control()')

        sleep(2)





def gpio_status():
    while True:
        try:
            write_gpio_status()
            tempfile = open('set_temp.txt', 'r')
            set_temperature = tempfile.read()
            tempfile.close()
            tempfile = open('room_temp.txt', 'r')
            room_temperature = tempfile.read()
            tempfile.close()
            tempfile = open('cond_temp.txt', 'r')
            condenser_temperature = tempfile.read()
            tempfile.close()

            compressor_state = GPIO.input(COMPRESSOR_PIN)
            fan_state = GPIO.input(FAN_PIN)
            heat_coil_state = GPIO.input(HEAT_COIL_PIN)
            heater_1_state = GPIO.input(HEATER_1_PIN)
            heater_2_state = GPIO.input(HEATER_2_PIN)

            print('Set temperature: ' + str(set_temperature))
            print('Room temperature: ' + str(room_temperature))
            #print('Condenser temperature: ' + str(condenser_temperature))
            print('Compressor state: ' + str(compressor_state))
            print('Fan state: ' + str(fan_state))
            print('Heat coil state: ' + str(heat_coil_state))
            print('Heater 1 state: ' + str(heater_1_state))
            print('Heater 2 state: ' + str(heater_2_state))


        except:
            print('Error in gpio_status()')

        sleep(1)





if __name__ == '__main__':
    process_1 = process_pool.submit(read_write_temps)
    thread_1 = thread_pool.submit(gpio_output_control)
    thread_2 = thread_pool.submit(gpio_status)
