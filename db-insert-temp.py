#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import sqlite3
import RPi.GPIO as GPIO

T_HIGH = 50
T_LOW = 45
fan_pin = 36

def get_cpu_temp():
    # 打开文件
    file = open("/sys/class/thermal/thermal_zone0/temp")
    # 读取结果，并转换为浮点数
    temp = float(file.read()) / 1000
    # 关闭文件
    file.close()
    return temp
def insert_cpu_temp(temp, open_fan_num, close_fan_num):
    # 连接数据库
    conn=sqlite3.connect('cpu.db')
    curs=conn.cursor()

    f = float(open_fan_num)/float((open_fan_num + close_fan_num)) * 100
    fans = "%.1f%%" % (f)
    # 插入数据库
    strtemp = "%.1f" % (temp);
    curs.execute("INSERT INTO temps(temperature, fan) VALUES((?),(?))", (strtemp, fans))
    conn.commit()

    # 关闭数据库
    conn.close()

def init_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(fan_pin, GPIO.OUT)
    # Close Fan
    GPIO.output(fan_pin, GPIO.LOW)

def process_fan(temp):
    if  temp > T_HIGH:
        GPIO.output(fan_pin, GPIO.HIGH)
        return 1
    elif temp < T_LOW:
        GPIO.output(fan_pin, GPIO.LOW)
        return 2
    return 0

def main():
    init_gpio()
    n_loop = 0
    case_open_fan_num = 0
    case_close_fan_num = 0

    fan_is_on = False

    temp = get_cpu_temp()
    insert_cpu_temp(temp, 0, 1)

    temp_sum = 0.0
    while True:
        temp = get_cpu_temp()
        temp_sum += temp;
        time.sleep(5)

        ret = process_fan(temp)
        if ret == 1:
            case_open_fan_num += 1;
            fan_is_on = True
        elif ret == 2:
            case_close_fan_num += 1;
            fan_is_on = False

        else:
            if fan_is_on == True:
                case_open_fan_num += 1
            else:
                case_close_fan_num += 1

        n_loop += 1
        if n_loop >= 60:
            temp = temp_sum / n_loop;
            insert_cpu_temp(temp, case_open_fan_num, case_close_fan_num)
            n_loop = 0
            temp_sum = 0.0
            case_open_fan_num = 0
            case_close_fan_num = 0


if __name__ == '__main__':
    main()
