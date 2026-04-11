'''
多颜色同时识别
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

# 设置颜色阈值，此处设置红绿蓝三种颜色的阈值
thresholds = [(4, 41, 27, 124, -6, 100),   # 红色阈值
              (21, 96, -49, -33, 20, 47),  # 绿色阈值
              (18, 32, -11, 17, -43, -13)]  # 蓝色阈值

# 初始化函数
def init_setup():
    global sensor, clock                   # 设置为全局变量
    sensor.reset()                         # 初始化感光元件
    sensor.set_pixformat(sensor.RGB565)    # 设置感光元件图像色彩格式为 RGB565 (RGB565为彩图，GRAYSCALE为灰度图)
    sensor.set_framesize(sensor.QVGA)      # 设置感光元件分辨率大小为 QVGA (QVGA是320x240)
    sensor.skip_frames(10)                 # 跳过一些帧，使以上的设置生效
    sensor.set_auto_gain(False)            # 关闭自动增益。在颜色识别中，需要关闭自动增益
    sensor.set_auto_whitebal(False)        # 关闭白平衡。白平衡是默认开启的，在颜色识别中，需要关闭白平衡
    clock = time.clock()                   # 创建时钟对象

# 主函数
def main():
    while 1:                               # 无限循环
        clock.tick()                       # 更新FPS帧率时钟
        img = sensor.snapshot()            # 拍一张照片并返回图像
        # 循环3种颜色阈值，在图像中查看是否有对应颜色并做一些操作，thresholds需为列表格式
        for blob in img.find_blobs(thresholds, pixels_threshold=200, area_threshold=200):
            img.draw_rectangle(blob.rect())        # 将目标颜色画框
            img.draw_cross(blob.cx(), blob.cy())   # 在目标颜色中心位置画个十字
        print("FPS %f" % clock.fps())  # 打印帧率

# 程序入口
if __name__ == '__main__':
    init_setup()                           # 执行初始化函数
    try:                                   # 异常处理
        main()                             # 执行主函数
    except:
        pass
