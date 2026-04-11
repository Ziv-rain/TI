# 二维码识别示例
#
# 这个例子展示了OpenMV Cam使用镜头校正来检测QR码的功能（请参阅qrcodes_with_lens_corr.py脚本以获得更高的性能）。
import sensor, image, time

# 初始化函数
def init_setup():
    global sensor, clock                       # 设置为全局变量
    sensor.reset()                             # 重置感光元件
    sensor.set_pixformat(sensor.RGB565)        # 此处设置的是彩色
    sensor.set_framesize(sensor.QVGA)          # 设置图像分辨率为QVGA，即320x240
    sensor.skip_frames(10)                     # 等待一些帧，使以上设置生效
    sensor.set_auto_gain(False)                # 必须关闭白平衡功能，以防止图像冲洗…
    clock = time.clock()                       # 创建时钟对象

# 主函数
def main():
    clock.tick()                           # 更新FPS帧率时钟
    img = sensor.snapshot()                # 拍一张图片并返回图像
    img.lens_corr(1.8)                     # 畸变矫正，1.8的强度参数对于2.8mm镜头来说是不错的。
    codes = img.find_qrcodes()             # 查找图像中的二维码
    for code in codes:
        img.draw_rectangle(code.rect(), color = (255, 0, 0))    # 用红线将二维码框出来
        #print(code)                        # 打印二维码的所有信息
        msg = code.payload()               # 获取二维码的内容
        print('二维码的内容为：%s' % msg)  # 打印二维码的内容
    if not codes:                          # 如果图像中未发现二维码时打印帧率，注:实际FPS更高，流FB使它更慢。
        print("FPS %f" % clock.fps())

# 程序入口
if __name__ == '__main__':
    init_setup()                               # 执行初始化函数
    try:
        while 1:
            main()                                 # 执行主函数
    except:
        pass
