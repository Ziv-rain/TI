# 线段检测例程
#
# 在图像中查找线段。对于在图像中找到的每个线对象，都会返回一个包含线条旋转的线对象。

# find_line_segments()找到有限长度的线（但是很慢）。
# 用find_line_segments()找到非无限的线（而且速度很快）。

enable_lens_corr = False                 # 畸变矫正，打开可以获得更直的线条…

import sensor, image, time

# 初始化函数
def init_setup():
    global sensor, clock                 # 设置为全局变量
    sensor.reset()                       # 重置感光元件
    sensor.set_pixformat(sensor.RGB565)  # 此处设置的是彩色，如果是灰度会更快
    sensor.set_framesize(sensor.QQVGA)   # 设置图像分辨率为QQVGA，即160x120
    sensor.skip_frames(time=2000)        # 等待2秒，使以上设置生效
    clock = time.clock()                 # 创建时钟对象

# 所有线段都有 `x1()`, `y1()`, `x2()`, 和`y2()` 方法来获得他们的终点
# 一个 `line()` 方法来获得所有上述的四个元组值，可用于 `draw_line()`.

# 主函数
def main():
    while 1:
        clock.tick()                     # 更新FPS帧率时钟
        img = sensor.snapshot()          # 拍一张图片并返回图像
        if enable_lens_corr:
            img.lens_corr(1.8)           # 畸变矫正，for 2.8mm lens...

        # `merge_distance`控制附近行的合并。 在0（默认），没有合并。
        # 在1处，任何距离另一条线一个像素点的线都被合并...等等，
        # 因为你增加了这个值。 您可能希望合并线段，因为线段检测会产生大量的线段结果。

        # `max_theta_diff` 控制要合并的任何两线段之间的最大旋转差异量。
        # 默认设置允许15度。

        for l in img.find_line_segments(merge_distance=0, max_theta_diff=5):
            img.draw_line(l.line(), color=(255, 0, 0))
            print(l)

        print("FPS %f" % clock.fps())    # 打印帧率，注:实际FPS更高，流FB使它更慢。

# 程序入口
if __name__ == '__main__':
    init_setup()  # 执行初始化函数
    try:
        main()    # 执行主函数
    except:
        pass
