# 人脸图片采集
#
# 采集人脸图片到openmv中
# 先在openmv的盘符中新建文件夹ZLTech，然后在该文件夹中新建文件夹s1，s2，要采集几个人就新建到s几
# 红灯亮做准备，蓝灯亮是正在拍照

import sensor, image, pyb

RED_LED_PIN = 1         # 红灯引脚
BLUE_LED_PIN = 3        # 蓝灯引脚
SAVE_PATH = 'ZLTech'    # 图片保存的位置
num = 1 # 设置被拍摄者序号，第一个人的图片保存到s1文件夹，第二个人的图片保存到s2文件夹，以此类推。每次更换拍摄者时，修改num值。

n = 20  # 设置每个人拍摄图片数量。

# 初始化函数
def init_setup():
    global sensor
    sensor.reset()                          # 初始化感光元件
    sensor.set_pixformat(sensor.GRAYSCALE)  # 设置图像格式为灰度图
    sensor.set_framesize(sensor.B128X128)   # 设置图像大小为128x128
    sensor.set_windowing((92,112))          # 设置窗口大小为92x112
    sensor.skip_frames(10)                  # 使以上设置生效
    sensor.skip_frames(time=2000)

# 主函数
def main():
    global n
    #连续拍摄n张照片，每间隔3s拍摄一次。
    while (n):
        #红灯亮
        pyb.LED(RED_LED_PIN).on()
        sensor.skip_frames(time=3000)   # 等待3s，准备一下表情。

        #红灯灭，蓝灯亮
        pyb.LED(RED_LED_PIN).off()
        pyb.LED(BLUE_LED_PIN).on()

        #保存截取到的图片到SD卡
        print(n)
        sensor.snapshot().save("%s/s%s/%s.pgm" % (SAVE_PATH, num, n) )  # or "example.bmp" (or others)

        n -= 1

        pyb.LED(BLUE_LED_PIN).off()     # 蓝灯灭
        print("Done! Reset the camera to see the saved image.")

# 程序入口
if __name__ == '__main__':
    init_setup()  # 执行初始化函数
    try:          # 异常处理
        main()    # 执行主函数
    except:
        pass
