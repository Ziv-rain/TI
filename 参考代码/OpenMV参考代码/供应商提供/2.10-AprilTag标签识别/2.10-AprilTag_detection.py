# AprilTag标签识别示例
import sensor, time

# 初始化函数
def init_setup():
    global sensor, clock                       # 设置为全局变量
    sensor.reset()                             # 重置感光元件
    sensor.set_pixformat(sensor.RGB565)        # 此处设置的是彩色
    sensor.set_framesize(sensor.QQVGA)         # 设置图像分辨率为QQVGA，即160x120
    sensor.skip_frames(time=2000)
    sensor.set_auto_gain(False)                # must turn this off to prevent image washout...
    sensor.set_auto_whitebal(False)            # must turn this off to prevent image washout...
    clock = time.clock()                       # 创建时钟对象

# 主函数
def main():
    clock.tick()                           # 更新FPS帧率时钟
    img = sensor.snapshot()                # 拍一张图片并返回图像
    apriltags = img.find_apriltags()       # 查找图像中的AprilTag
    for tag in apriltags:
        img.draw_rectangle(tag.rect, color=(255, 0, 0))    # 用红线将AprilTag框出来
        img.draw_cross(tag.cx, tag.cy, color=(0, 255, 0))
        #print(tag)                        # 打印AprilTag的所有信息
        apriltag_id = tag.id               # 获取AprilTag的id
        apriltag_family = tag.name         # 获取AprilTag所属家族
        print('AprilTag的id为 %s，所属家族为 %s' % (apriltag_id, apriltag_family))  # 打印AprilTag的id及所属家族
    #if not apriltags:                      # 如果图像中未发现AprilTag时打印帧率，注:实际FPS更高，流FB使它更慢。
        #print("FPS %f" % clock.fps())

# 程序入口
if __name__ == '__main__':
    init_setup()                                # 执行初始化函数
    try:
        while 1:
            main()                              # 执行主函数
    except:
        pass
