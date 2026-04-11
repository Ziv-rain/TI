# 矩形识别例程
#
# 使用april标签代码中的四元检测代码在图像中找到矩形。
# 四元检测算法以非常稳健的方式检测矩形，并且比基于霍夫变换的方法好得多。
# 例如，即使镜头失真导致这些矩形看起来弯曲，它仍然可以检测到矩形。 圆角矩形是没有问题的！
# (但是，这个代码也会检测小半径的圆)...

import sensor, time

# 初始化函数
def init_setup():
    global sensor, clock                 # 设置为全局变量
    sensor.reset()                       # 重置感光元件
    sensor.set_pixformat(sensor.RGB565)  # 将图像格式设置为彩色
    sensor.set_framesize(sensor.QQVGA)   # 设置图像分辨率为QQVGA，即160x120
    sensor.skip_frames(10)               # 跳过10帧，使以上设置生效
    clock = time.clock()                 # 创建时钟对象

# 主函数
def main():
    clock.tick()                     # 更新FPS帧率时钟
    img = sensor.snapshot()          # 拍一张图片并返回图像

    # 下面的`threshold`应设置为足够高的值，以滤除在图像中检测到的具有低边缘幅度的噪声矩形。最适用与背景形成鲜明对比的矩形。
    for r in img.find_rects(threshold=15000):
        img.draw_rectangle(r.rect(), color=(255, 0, 0))        # 用红线框出矩形
        for p in r.corners():
            img.draw_circle(p[0], p[1], 5, color=(0, 255, 0))  # 在矩形端点处画绿色圆
        print(r)

    print("FPS %f" % clock.fps())    # 打印帧率，注:实际FPS更高，流FB使它更慢。

# 程序入口
if __name__ == '__main__':
    init_setup()  # 执行初始化函数
    try:
        while 1:
            main()    # 执行主函数
    except:
        pass
