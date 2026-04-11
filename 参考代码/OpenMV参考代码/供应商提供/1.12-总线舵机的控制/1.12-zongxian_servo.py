'''
总线舵机的控制
此处控制总线舵机之前需要先给每个舵机设定ID，我们建议云台底部舵机ID设为000，云台上方ID设为001
使用openmv的串口3，波特率为115200
通过串口发送指令字符串来控制
指令格式为 #idPpwmTtime!
其中id：云台底部舵机ID设为000，云台上方ID设为001
pwm范围为0500-2500，复位状态为1500
time为时间（毫秒为单位）

'''
import time
from pyb import UART

# 初始化函数
def init_setup():
    global uart3              # 设置为全局变量
    uart3 = UART(3, 115200)   # 实例化串口3，波特率设置为115200

# 云台复位
def middle():
    uart3.write('#000P1500T1000!#001P1500T1000!')
    time.sleep(1)             # 延时1秒

# 主函数
def main():
    for i in range(3):
        uart3.write('#000P1000T1000!#001P1000T1000!')  # 后退1秒
        time.sleep(1)         # 延时1秒
        uart3.write('#000P2000T1000!#001P2000T1000!')  # 前进1秒
        time.sleep(1)         # 延时1秒

# 程序入口
if __name__ == '__main__':
    init_setup()              # 执行初始化函数初始化串口
    try:                      # 异常处理
        main()                # 执行主函数
    finally:
        middle()
