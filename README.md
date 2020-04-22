## RPi temperature & fan control

   本文使用python实现对树莓派的温度实时检测和风扇的控制，并把相关的温度，风扇控制信息保存到sqlite数据库中。

1. ***创建数据库和空表***

​    a.  在文件 ***create-table-only.sql***定义一个表temps, 共4个字段: 其中 ***name***,  ***tdatetime***有默认值, 

​         ***temperature*** 记录当前温度, ***fan*** 记录风扇的使用率；

```
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE temps(
    name DEFAULT 'RPi.CPU',
    tdatetime DATETIME DEFAULT (datetime('now', 'localtime')),
    temperature NUMERIC NOT NULL,
    fan NUMERIC NOT NULL
);
COMMIT;
```



   b.  写一个shell脚本 ***create-table-only.sh***, 用于创建一个空表：

```
#!/bin/sh
DBNAME="cpu.db"
rm -f $DBNAME
echo 开始插入数据
sqlite3 $DBNAME < create-table-only.sql
echo 插入完成
```

​     给shell文件新增可执行权限, 运行后生成数据库文件  ***cpu.db***：

```
chmod +x create-table-only.sh
./create-table-only.sh
```



2. ***用python读取温度,控制风扇，并保存到数据库***

​      创建文件 ***db-insert-temp.py***

```
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
```

***简要说明***

a. 从文件 ***/sys/class/thermal/thermal_zone0/temp*** 读取树莓派的当前温度，

​    也可以用命令 ***/opt/vc/bin/vcgencmd measure_temp***得到树莓派的温度；

b. 风扇控制, 树莓派的GPIO分布如下:

![rpi](raspi.png)

 风扇的控制电路如下：

![fan](fan_sch.png)

   ***说明:*** 按BOARD引脚编码, +5V为4脚，GND接到6脚，用36脚控制NPN开关：

```
fan_pin = 36
def init_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(fan_pin, GPIO.OUT)
    # Close Fan
    GPIO.output(fan_pin, GPIO.LOW)
```

在这里，温度超过50度时打开风扇，小于45度时关闭风扇：

```
T_HIGH = 50
T_LOW = 45
def process_fan(temp):
    if  temp > T_HIGH:
        GPIO.output(fan_pin, GPIO.HIGH)
        return 1
    elif temp < T_LOW:
        GPIO.output(fan_pin, GPIO.LOW)
        return 2
    return 0
```



​    C. 在程序中，加入了温度和风扇使用率的统计，并写数据库：

```
.
.
.
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
            
```



运行时查看数据结果：

```
sqlite3 cpu.db
再输入 SELECT * FROM temps;
2020-04-22T10:03:14Z,47.4,63.3%
2020-04-22T10:08:15Z,48.1,35.0%
2020-04-22T10:13:15Z,46.2,43.3%
2020-04-22T10:18:15Z,47  ,71.7%
2020-04-22T10:23:16Z,47.9,36.7%
```

3. ***设置开机启动***

a. 启动脚本 ***auto-start.sh***

```
#!/bin/bash
cd /home/pi/work/py/temp
python db-insert-temp.py &
```

用shell脚本来启动python文件, 注意要为auto-start.sh 增加可执行权限：

```
chmod +x auto-start.sh 
```

b. 设置启动项, 在/etc/init.d 下编辑文件temp-app

```
sudo vim /etc/init.d/temp-app 
```

内容如下：

```
#!/bin/sh
#/etc/init.d/init-app
 
### BEGIN INIT INFO
# Provides:          get-ip-address
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: init-app
# Description: This service is used to start init shell
### END INIT INFO
 
case "$1" in
    start)
        echo "Starting temp service"
        su pi -c "exec /home/pi/work/py/temp/auto-start.sh"
         ;;
    stop)
        echo "Stop"
        ;;
 
    *)
        echo "Usage: service temp-app start|stop"
        exit 1
        ;;
esac
exit 0
```

保存后，设置开机启动：

```
sudo update-rc.d temp-app defaults
```

重启树莓派就可以自动启动程序了, 也可以先手动启动:

```
sudo service temp-app start
```

