# 条形码识别例程
#
# 使用OpenMV来检测条形码。条形码检测不适用于M4相机。

import sensor, image, time, math

# 初始化函数
def init_setup():
    global sensor, clock                      # 设置为全局变量
    sensor.reset()                            # 重置感光元件
    sensor.set_pixformat(sensor.GRAYSCALE)    # 此处设置的是灰度
    sensor.set_framesize(sensor.VGA)          # 设置图像分辨率为VGA，即640x480
    sensor.set_windowing((640, 80))           # V Res of 80 == less work (40 for 2X the speed).
    sensor.skip_frames(time=2000)             # 等待2秒，使以上设置生效
    sensor.set_auto_gain(False)               # 必须关闭此功能，以防止图像冲洗…
    sensor.set_auto_whitebal(False)           # 必须关闭此功能，以防止图像冲洗…
    clock = time.clock()                      # 创建时钟对象

    # 条形码检测可以在OpenMV Cam的OV7725相机模块的640x480分辨率下运行。
    # 条码检测也可在RGB565模式下工作，但分辨率较低。
    # 也就是说，条形码检测需要更高的分辨率才能正常工作，因此应始终以640x480的灰度运行。

# 判断条形码类型的函数
def barcode_name(code):
    if(code.type() == image.EAN2):
        return "EAN2"
    if(code.type() == image.EAN5):
        return "EAN5"
    if(code.type() == image.EAN8):
        return "EAN8"
    if(code.type() == image.UPCE):
        return "UPCE"
    if(code.type() == image.ISBN10):
        return "ISBN10"
    if(code.type() == image.UPCA):
        return "UPCA"
    if(code.type() == image.EAN13):
        return "EAN13"
    if(code.type() == image.ISBN13):
        return "ISBN13"
    if(code.type() == image.I25):
        return "I25"
    if(code.type() == image.DATABAR):
        return "DATABAR"
    if(code.type() == image.DATABAR_EXP):
        return "DATABAR_EXP"
    if(code.type() == image.CODABAR):
        return "CODABAR"
    if(code.type() == image.CODE39):
        return "CODE39"
    if(code.type() == image.PDF417):
        return "PDF417"
    if(code.type() == image.CODE93):
        return "CODE93"
    if(code.type() == image.CODE128):
        return "CODE128"

# 主函数
def main():
    while 1:
        clock.tick()                          # 更新FPS帧率时钟
        img = sensor.snapshot()               # 拍一张图片并返回图像
        codes = img.find_barcodes()           # 从图像中查找条形码
        for code in codes:
            img.draw_rectangle(code.rect())
            print_args = (barcode_name(code), code.payload(), (180 * code.rotation())/math.pi, code.quality(), clock.fps())
            print("Barcode %s, Payload \"%s\", rotation %f (degrees), quality %d, FPS %f" % print_args)
            msg = code.payload()              # 条形码的信息
            print('条形码信息为：%s' % msg)   # 打印条形码的内容
        if not codes:                         # 如果图像中未发现条形码时打印帧率，注:实际FPS更高，流FB使它更慢。
            print("FPS %f" % clock.fps())

# 程序入口
if __name__ == '__main__':
    init_setup()                              # 执行初始化函数
    try:
        main()                                # 执行主函数
    except:
        pass
