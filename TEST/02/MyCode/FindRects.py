'''
实验名称:矩形检测
实验平台:01Studio CanMV K230
教程:wiki.01studio.cc
说明:推荐使用320x240以下分辨率，分辨率过大会导致帧率下降。
'''

import time

from media.sensor import *  #导入sensor模块，使用摄像头相关接口
from media.display import *  #导入display模块，使用display相关接口
from media.media import *  #导入media模块，使用meida相关接口

#导入串口模块
from machine import UART
from machine import FPIOA

fpioa = FPIOA()  # 初始化一个 FPIOA 硬件控制器

# UART1代码
# TX1(GPIO3), RX1(GPIO4)
fpioa.set_function(3, FPIOA.UART1_TXD)
fpioa.set_function(4, FPIOA.UART1_RXD)

uart = UART(UART.UART1, 115200)  #设置串口号1和波特率115200
# uart.write('Hello 01Studio!')  #测试UART发送功能

# 全局变量
seq = 0  # UART数据帧序列号(0~255循环)


def send_center(uart, x, y):
    """
    通过UART接口发送中心坐标数据帧。

    该函数将给定的x、y坐标打包成自定义协议的数据帧，并通过指定的UART接口发送。
    数据帧包含帧头、消息ID、序列号、坐标数据和校验和，总长度为9字节。

    参数:
        uart: UART接口对象，需支持write()方法用于发送数据
        x (int or float): X轴坐标值，将被转换为整数
        y (int or float): Y轴坐标值，将被转换为整数

    返回值:
        无
    """
    global seq
    x = int(x)
    y = int(y)

    # 初始化帧数据，总长度为9字节
    frame = bytearray(9)

    frame[0] = 0xAA               # 帧头
    frame[1] = 0x55               # 帧头
    frame[2] = 0x01               # MSG_ID: center
    frame[3] = seq                # 递增序号(0~255循环)
    frame[4] = x & 0xFF           # 取 x 的低8位
    frame[5] = (x >> 8) & 0xFF    # 取 x 的高8位
    frame[6] = y & 0xFF           # 取 y 的低8位
    frame[7] = (y >> 8) & 0xFF    # 取 y 的高8位
    # 计算校验和(对消息ID到Y坐标高位共6个字节进行异或)
    chk = 0
    for b in frame[2:8]:          # 遍历从 frame[2] 到 frame[7]（共6个字节：MSG_ID、seq、x_low、x_high、y_low、y_high）。
        chk ^= b                  # 对每个字节进行异或
    frame[8] = chk                # 将计算出的校验和存入第9字节

    # 通过uart发送帧数据
    uart.write(frame)
    seq = (seq + 1) & 0xFF


sensor = Sensor(width=1280, height=960)  #构建摄像头对象
sensor.reset()  #复位和初始化摄像头
sensor.set_framesize(width=320, height=240)  #设置帧大小为LCD分辨率(800x480)，默认通道0
sensor.set_pixformat(Sensor.RGB565)  #设置输出图像格式，默认通道0

Display.init(Display.ST7701, to_ide=True)  #同时使用3.5寸mipi屏和IDE缓冲区显示图像，800x480分辨率
#Display.init(Display.VIRT, sensor.width(), sensor.height()) #只使用IDE缓冲区显示图像

MediaManager.init()  #初始化media资源管理器

sensor.run()  #启动sensor

clock = time.clock()

while True:
    clock.tick()

    img = sensor.snapshot()  #拍摄一张图片

    max_area = 0
    best_rect = None
    best_corners = None
    # `threshold` 需要设置一个比价大的值来过滤掉噪声。
    #这样在图像中检测到边缘亮度较低的矩形。矩形
    #边缘量级越大，对比越强…

    for r in img.find_rects(threshold=20000):
        # 增加过滤条件，排除掉过小的矩形，避免误检。根据实际情况调整数值。
        # 只有当高度大于50，且宽度大于50时，才认为是有效矩形
        if r.h() > 50 and r.w() > 50:
            area = r.w() * r.h()
            if area > max_area:
                max_area = area
                best_rect = r.rect()      # 存值，不存 r 对象
                best_corners = r.corners()

    if best_rect is not None:
        # 绘制检测到的四边形(红色框)
        img.draw_rectangle(best_rect, color=(255, 0, 0), thickness=2)
        # 绘制四个角点(绿色圆点)
        for p in best_corners:
            img.draw_circle(p[0], p[1], 5, color=(0, 255, 0))

        # 计算中心坐标

        # 方法一:使用外接矩形计算几何中心 (简单快速)
        # center_x = r.x() + r.w() / 2
        # center_y = r.y() + r.h() / 2

        # 方法二:使用四个角点计算质心中心 (更精确，适用于透视畸变)
        center_x = (best_corners[0][0] + best_corners[1][0] + best_corners[2][0] + best_corners[3][0]) / 4
        center_y = (best_corners[0][1] + best_corners[1][1] + best_corners[2][1] + best_corners[3][1]) / 4

        # 在中心点画一个十字准星(黄色)
        img.draw_cross(int(center_x),
                       int(center_y),
                       color=(255, 255, 0),
                       size=10,
                       thickness=2)

        # 打印坐标信息
        # 格式:Center: (x坐标, y坐标)
        print(f"Center: ({int(center_x)}, {int(center_y)})")
        send_center(uart, center_x, center_y)
        # print(r)

    #Display.show_image(img) #显示图片

    #显示图片，仅用于LCD居中方式显示
    Display.show_image(img,
                       x=round((800 - sensor.width()) / 2),
                       y=round((480 - sensor.height()) / 2))

    #print(clock.fps())   #打印FPS
