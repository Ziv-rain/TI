# 测量物体实际大小
# 注意：此处是利用固定距离和比例系数来计算物体大小。
# 注意：环境光会对识别有影响，找比较合适的环境来运行此程序。
# 当测另一个物体的大小时，需要将该物体放在求比例系数K时的那个距离处，此处我们使用的是10cm处
import sensor, image, time

# 此处通过识别物体的颜色来测大小
target_threshold = (91, 65, -15, 33, 89, 47)   # 此处以黄色为例

K = 0.07                                  # 当测另一个物体的大小时，需要将该物体放在求比例系数K时的那个距离处，此处我们使用的是10cm处
# 实际大小 = 直径的像素 * K。
# 第一次时，可以将小球放在距离摄像头10cm处的位置，测得Lm的大小之后，K = 实际大小 / Lm
# 比如在10cm处时，直径的像素为43，小球实际大小为3cm，则K = 3 / 43 = 0.07，具体情况以你的实际情况为准

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

        blobs = img.find_blobs([target_threshold])  # 找到图像中的目标区域
        if len(blobs) == 1:
            b = blobs[0]
            img.draw_rectangle(b[0:4])    # 将目标区域框出来
            img.draw_cross(b[5], b[6])    # 在目标中心位置画十字
            Lm = (b[2]+b[3])/2            # 获取像素点
            w = K * b[2]                  # 通过比例系数K和像素值得到物体实际宽度
            h = K * b[3]                  # 通过比例系数K和像素值得到物体实际高度
            print('物体实际宽度为 %s cm' % w)  # 打印物体实际宽度值
            print('物体实际高度为 %s cm' % h)  # 打印物体实际高度值
            #print(Lm)                     # 打印像素点数，在你对一个新的物体进行测大小时，需要将该物体放在求比例系数K时的那个距离处，此处我们使用的是10cm处
        #print(clock.fps())              # 打印帧率，注:实际FPS更高，流FB使它更慢。

# 程序入口
if __name__ == '__main__':
    init_setup()  # 执行初始化函数
    try:
        main()    # 执行主函数
    except:
        pass
