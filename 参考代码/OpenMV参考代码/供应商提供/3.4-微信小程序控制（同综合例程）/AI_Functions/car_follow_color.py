# 追小球的小车
import sensor, image, time
from pyb import LED
from ZL_SDK import zl_car_run, zl_pan_tilt, zl_uart3
from ZL_SDK.pid import PID

target_threshold = (15, 58, 39, 74, 62, 18)    # 颜色阈值
size_threshold = 475                           # 定义一个目标阈值区域的像素点数，小于这个阈值时使小车前进，大于这个阈值时使小车后退
x_pid = PID(p=0.7, i=1, imax=100)              # 控制小车方向
h_pid = PID(p=0.13, i=0.1, imax=50)            # 控制小车速度

# 初始化函数
def init_setup():
    global sensor, clock                       # 设置为全局变量
    sensor.reset()                             # 初始化感光元件
    sensor.set_vflip(True)
    sensor.set_hmirror(True)
    sensor.set_pixformat(sensor.RGB565)        # 将图像格式设置为彩色
    sensor.set_framesize(sensor.QQVGA)         # 将图像大小设置为QQVGA，即160*120
    sensor.skip_frames(10)                     # 跳过10帧使以上设置生效
    sensor.set_auto_whitebal(False)            # 关闭白平衡
    clock = time.clock()                       # 创建时钟对象
    zl_pan_tilt.main(0, -50)                   # 云台倾斜向下，方便查找目标


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
    clock.tick()                                                   # 更新FPS帧率时钟
    img = sensor.snapshot()                                        # 拍一张照片并返回图像

    blobs = img.find_blobs([target_threshold])                     # 在图像中查找目标颜色区域
    if blobs:                                                      # 当查找到目标颜色区域后
        max_blob = find_max(blobs)                                 # 查找图像中最大的目标色块
        x_error = max_blob[5] - img.width() / 2                    # x轴差值
        print(max_blob[2]*max_blob[3])
        h_error = max_blob[2] * max_blob[3] - size_threshold       # 面积差值
        print("x error: %s , h error: %s" % (x_error, h_error))
        img.draw_rectangle(max_blob[0:4])                          # 将找到的目标颜色区域用矩形框出来
        img.draw_cross(max_blob[5], max_blob[6])                   # 在目标颜色区域的中心点处画十字
        x_output = x_pid.get_pid(x_error, 1)
        h_output = h_pid.get_pid(h_error, 1)
        print("x_output %s ,h_output %s" % (x_output, h_output))
        zl_car_run.car_run(int(-h_output-x_output)*10, int(-h_output+x_output)*10)  # 小车开始追小球
    else:
        zl_car_run.car_run(400, -400)                              # 当未找到目标颜色区域时，让小车原地转圈找寻目标颜色

# 程序入口
if __name__ == '__main__':
    init_setup()                # 执行初始化函数
    zl_uart3.init_setup()       # 串口初始化
    try:
        while 1:
            main()              # 执行主函数
    except:
        zl_pan_tilt.middle()    # 云台复位
        zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.stop_speed)  # 小车停止
