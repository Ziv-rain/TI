'''
马达的控制
此处控制马达用到了我们的总线双路驱动模块
使用openmv的串口3，波特率为115200
通过串口发送指令字符串来控制
指令格式为 #idPpwmTtime!
其中id我们需要设置总线双路驱动的id为006，以马达接口朝上的方向，则左轮马达接左侧马达接口，右轮马达接右侧马达接口
pwm范围为0500-2500，中位为1500,当pwm值小于1500或大于1500时为正转或反转，具体视马达安装方向而定
time为时间（毫秒为单位），如果是0000则电机一直转

'''
import time
from pyb import UART

# 初始化函数
def init_setup():
    global uart3              # 设置为全局变量
    uart3 = UART(3, 115200)   # 实例化串口3，波特率设置为115200

# 马达停止转动
def middle():
    uart3.write('#006P1500T0000!#007P1500T0000!')

# 主函数
def main():
    for i in range(3):
        uart3.write('#006P1200T1000!#007P1800T1000!')  # 后退1秒
        time.sleep(1)         # 延时1秒
        uart3.write('#006P1800T1000!#007P1200T1000!')  # 前进1秒
        time.sleep(1)         # 延时1秒

# 程序入口
if __name__ == '__main__':
    init_setup()              # 执行初始化函数初始化串口
    try:                      # 异常处理
        main()                # 执行主函数
    finally:
        middle()
