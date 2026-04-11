'''
云台pwm舵机控制
度数为180度（-90度-90度）
可用的pwm口有P7 P8 P9，在我们的扩展板上使用的是P7和P8引脚
'''
from pyb import Servo
from time import sleep

# 实例化云台的两个舵机，pan为下面那个舵机，tilt为上方那个舵机
pan = Servo(1)                 # 使用的P7引脚
tilt = Servo(2)                # 使用的P8引脚

# 舵机回归到中位，即90度位置
def middle():
    pan.angle(0, 1000)         # pan舵机在1秒内转动到0度位置
    tilt.angle(0, 1000)        # tilt舵机在1秒内转动到0度位置
    sleep(1)                   # 延时1秒

# 主函数
def main(pan_angle, tilt_angle):
    global pan，tilt
    pan.angle(pan_angle)       # pan舵机转动到pan_angle度位置
    tilt.angle(tilt_angle)     # tilt舵机转动到tilt_angle度位置

# 程序入口
if __name__ == '__main__':
    try:                       # 异常处理
        main(45, 45)           # 执行主函数
    finally:
        middle()               # 程序结束时使舵机回到0度位置
