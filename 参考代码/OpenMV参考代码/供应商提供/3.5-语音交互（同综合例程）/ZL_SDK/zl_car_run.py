from ZL_SDK import zl_uart3

forward_speed = 400              # 前进速度
backward_speed = -400            # 后退速度
stop_speed = 0                   # 停车速度

'''
通过串口发送指令控制电机的转速,时间
参数：
speed_left---左轮
speed_right---右轮
(-1000~1000)负值后退，正值前进，绝对值越大转速越高。
time 代表车轮转动时间，0代表一直转动，1000代表转动1秒，以此类推。
'''
def car_run(speed_left, speed_right, time=0):
    textStr = '#006P{0:0>4d}T{2:0>4d}!#007P{1:0>4d}T{2:0>4d}!'.format(1500+speed_left, 1500-speed_right, time)
    print(textStr)
    zl_uart3.uart3_send(textStr)

# 程序入口
if __name__ == '__main__':
    zl_uart3.init_setup()        # 串口初始化
    try:                         # 异常处理
        car_run(forward_speed, forward_speed, 2000)     # 前进2秒
        while 1:
            pass
    except:
        car_run(stop_speed, stop_speed)                 # 停车

