# 测距
# 注意：此处是利用参照物的大小比例来计算距离。
# 注意：环境光会对识别有影响，找比较合适的环境来运行此程序。
# 此种方法只适用于特定大小的物体，当换另一个物体时，就需要重新来确定比例系数K的值了
import sensor, image, time

# 此处通过识别物体的颜色来测距，当然也可换成其他方式来识别
target_threshold = (44, 63, 69, 89, 22, 77)  # 此处以红色为例
#target_threshold = (10, 63, 9, 127, -20, 55)

K = 430                                   # 对某个物体进行测距的第一次需要先确定比例系数K的大小
# K = 直径的像素 * 距离。
# 第一次时，可以将小球放在距离摄像头10cm处的位置，测得Lm的大小之后，K = 10 * Lm
# 比如在10cm处时，直径的像素为43，则K = 10 * 43 = 430，具体情况以你的实际情况为准

# 初始化函数
def init_setup():
    global sensor, clock                  # 设置为全局变量
    sensor.reset()                        # 初始化感光元件
    sensor.set_pixformat(sensor.RGB565)   # 将图像格式设置为彩色
    sensor.set_framesize(sensor.QQVGA)    # 将图像大小设置为160x120
    sensor.skip_frames(10)                # 跳过10帧，使以上设置生效
    sensor.set_auto_whitebal(False)       # 关闭白平衡
    clock = time.clock()                  # 创建时钟对象

# 主函数
def main():
    while 1:
        clock.tick()                      # 更新FPS帧率时钟
        img = sensor.snapshot()           # 拍一张照片并返回图像

        blobs = img.find_blobs([target_threshold])  # 找到图像中的红色区域
        if len(blobs) == 1:
            b = blobs[0]
            img.draw_rectangle(b[0:4])    # 将红色区域框出来
            img.draw_cross(b[5], b[6])    # 在红色中心位置画十字
            Lm = (b[2]+b[3])/2            # 获取像素点
            length = K/Lm                 # 通过比例系数K得到物体距离
            print('摄像头距离物体：%s cm' % length)  # 打印距离值
            #print(Lm)                     # 打印像素点数，在你对一个新的物体进行测距时，需要先获取它的像素点数来得到比例系数K
        #print(clock.fps())              # 打印帧率，注:实际FPS更高，流FB使它更慢。

# 程序入口
if __name__ == '__main__':
    init_setup()  # 执行初始化函数
    try:
        main()    # 执行主函数
    except:
        pass
