from pyb import LED
from time import sleep

# 初始化函数
def init_setup():
    global led              # 设置为全局变量
    led = LED(1)            # 1为红色，2为绿色，3为蓝色
    led.off()               # 灯灭

# 主函数
def main(delay_time=1):
    led.toggle()            # 灯亮灭反转
    sleep(delay_time)       # 默认延时1秒

# 程序入口
if __name__ == '__main__':
    init_setup()            # 执行初始化函数
    try:                    # 异常处理
        while 1:            # 无限循环
            main()          # 执行主函数
    except:
        led.off()           # 程序异常时让灯灭
