# 串口收发数据
#
# This example shows how to use the serial port on your OpenMV Cam. Attach pin
# P4 to the serial input of a serial LCD screen to see "Hello World!" printed
# on the serial LCD display.

from pyb import UART
import time

def init_setup(baud=115200):
    global uart3
    uart3 = UART(3, baud)                  # 初始化串口3，设置波特率为115200
    uart3.init(115200,8,None,1)
    print('串口初始化完成')

# 串口接收数据
def uart3_recv():
    recv_data = uart3.read()
    print('recv data: %s' % recv_data)
    return recv_data

# 串口发送数据
def uart3_send(send_data):
    global uart3
    uart3.write(send_data)

# 主函数
def main():
    if uart3.any():
        data = uart3_recv()              # 串口接收数据
        print('uart3 recv: %s' % data)   # 打印串口接收到的数据
        print(1)
        uart3_send(data)                 # 串口将接收到的数据再通过串口发送出去了

# 程序入口
if __name__ == '__main__':
    init_setup()                         # 执行初始化函数
    try:
        while 1:
            main()                       # 执行主函数
    except:
        pass
