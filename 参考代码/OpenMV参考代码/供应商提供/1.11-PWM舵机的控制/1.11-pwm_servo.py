'''
pwm舵机控制
度数为180度（-90度-90度）
可用的pwm口有P7 P8 P9，在我们的扩展板上使用的是P7和P8引脚
'''
from pyb import Servo
from time import sleep

# 实例化两个舵机
s1 = Servo(1)                # 使用的P7引脚
s2 = Servo(2)                # 使用的P8引脚

# 舵机回归到中位，即90度位置
def middle():
    s1.angle(0, 1000)        # s1舵机在1秒内转动到0度位置
    s2.angle(0, 1000)        # s2舵机在1秒内转动到0度位置
    sleep(1)                 # 延时1秒

# 主函数
def main():
    global s1, s2
    for i in range(3):       # 循环执行3次
        s1.angle(-45, 1500)  # s1舵机在1.5秒内转动到0度位置
        s2.angle(-45, 1500)  # s2舵机在1.5秒内转动到0度位置
        sleep(1.5)           # 延时1.5秒
        s1.angle(45, 1500)   # s1舵机在1.5秒内转动到0度位置
        s2.angle(45, 1500)   # s2舵机在1.5秒内转动到0度位置
        sleep(1.5)           # 延时1.5秒

# 程序入口
if __name__ == '__main__':
    try:                     # 异常处理
        main()               # 执行主函数
    finally:
        middle()             # 程序结束时使舵机回到0度位置
