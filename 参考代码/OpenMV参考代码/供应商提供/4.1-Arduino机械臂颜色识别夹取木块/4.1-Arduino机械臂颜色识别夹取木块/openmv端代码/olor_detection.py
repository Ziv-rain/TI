'''
颜色识别夹取木块
红色木块放在正前方，绿色木块放在小车左侧，蓝色木块放在小车右侧
红绿蓝三种颜色可以同时识别，还可自行添加其他颜色阈值来识别其他颜色
# 注意：环境光会对识别有影响，找比较合适的环境来运行此程序。
颜色阈值采集方法：
方法一：
    1.可以在‘工具’-->‘机器视觉’-->‘阈值编辑器’-->‘帧缓冲区’中采集，
    2.拖动6个滑块来调整图像，直到要采集的颜色都呈白色，其他都呈黑色为止，
    3.采集好之后将LAB阈值复制到代码中的阈值处使用即可。
方法二：
    1.可以在右侧‘帧缓冲区’和‘直方图’的’LAB色彩空间‘配合采集
    2.先在帧缓冲区中用鼠标左键框出要采集的颜色区域，
    3.然后在直方图中的LAB色彩空间中，分别复制L、A、B的最小值和最大值到代码中的颜色阈值元组中使用即可
'''
import sensor, time
from pyb import UART
import utime
import json


target_color_appear_count = 0

# 设置颜色阈值，此处设置红绿蓝三种颜色的阈值
thresholds = {'red': (62, 41, -9, 113, 24, 98),       # 红色阈值
              'green': (68, 26, -57, -18, 100, -81),  # 绿色阈值
              'blue': (70, 6, -76, 36, -20, -96)      # 蓝色阈值
            }
# 各颜色对应要执行的动作组
actions = {'start': '$DGT:3-3,1!',
           'red': '$DGT:4-10,1!',
           'green': '$DGT:11-19,1!',
           'blue': '$DGT:20-28,1!'
            }

# 初始化函数
def init_setup():
    global sensor, clock, uart3            # 设置为全局变量
    sensor.reset()                         # 初始化感光元件
    sensor.set_pixformat(sensor.RGB565)    # 设置感光元件图像色彩格式为 RGB565 (RGB565为彩图，GRAYSCALE为灰度图)
    sensor.set_framesize(sensor.QVGA)      # 设置感光元件分辨率大小为 QVGA (QVGA是320x240)
    sensor.skip_frames(10)                 # 跳过一些帧，使以上的设置生效
    sensor.set_auto_gain(False)            # 关闭自动增益。在颜色识别中，需要关闭自动增益
    sensor.set_auto_whitebal(False)        # 关闭白平衡。白平衡是默认开启的，在颜色识别中，需要关闭白平衡
    clock = time.clock()                   # 创建时钟对象
    uart3 = UART(3, 115200)                # 初始化串口3，设置波特率为115200
    print('初始化完成')
    utime.sleep(2)
    uart3_send(actions['start'])
    utime.sleep(2)


# 串口接收数据
def uart3_recv():
    recv_data = uart3.read()
    print('recv data: %s' % recv_data)
    return recv_data

# 串口发送数据
def uart3_send(send_data):
    global uart3
    uart3.write(send_data)


# 查找图像中最大的色块
def find_max(blobs):
    max_size = 0
    for blob in blobs:
        if blob[2] * blob[3] > max_size:
            max_blob = blob
            max_size = blob[2] * blob[3]
    return max_blob

# 主函数
def main():
    global target_color_appear_count
    while 1:                               # 无限循环
        clock.tick()                       # 更新FPS帧率时钟
        img = sensor.snapshot()            # 拍一张照片并返回图像
        # 循环3种颜色阈值，在图像中查看是否有对应颜色并做一些操作，thresholds需为字典格式
        for threshold in thresholds:
            blobs = img.find_blobs([thresholds[threshold]])                # 在图像中查找目标颜色区域
            if blobs:                                                      # 当查找到目标颜色区域后
                max_blob = find_max(blobs)                                 # 查找图像中最大的目标色块
                img.draw_rectangle(max_blob[0:4])                          # 将找到的目标颜色区域用矩形框出来
                img.draw_cross(max_blob[5], max_blob[6])                   # 在目标颜色区域的中心点处画十字
                target_area = max_blob[2] * max_blob[3]                    # 面积
                print('area is  ', target_area)                            # 打印面积

                if 2000 < target_area < 6000:                              # 面积合适时
                    target_color_appear_count += 1

                if target_color_appear_count > 5:                          # 识别到的面积合适时的次数大于5次时串口发数据
                    if threshold == 'red':
                        uart3_send(actions['red'])                         # 串口将识别到的颜色对应的动作组发出去
                        utime.sleep(15)                                    # 延时以便让动作组执行完成
                    elif threshold == 'green':
                        uart3_send(actions['green'])                       # 串口将识别到的颜色对应的动作组发出去
                        utime.sleep(18)                                    # 延时以便让动作组执行完成
                    elif threshold == 'blue':
                        uart3_send(actions['blue'])                        # 串口将识别到的颜色对应的动作组发出去
                        utime.sleep(18)                                    # 延时以便让动作组执行完成
                    print('uart3 send color is ', threshold)
                    target_color_appear_count = 0


# 程序入口
if __name__ == '__main__':
    init_setup()                           # 执行初始化函数
    try:                                   # 异常处理
        main()                             # 执行主函数
    except:
        pass
