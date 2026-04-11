# 巡线小车
# 使用快速线性回归来实现
# 快速线性回归，可以使用get_regression快速返回视野中的一条回归直线，
# 可以得到直线的角度theta、直线的偏移距离rho，然后根据角度和偏移距离动态的调整小车的速度
import sensor, image, time
from pyb import LED
from ZL_SDK import zl_car_run, zl_pan_tilt, zl_uart3
from ZL_SDK.pid import PID

THRESHOLD = (32, 6, -23, 9, -18, 45)       # 线的颜色阈值，此处为白底黑线

rho_pid = PID(p=0.8, i=0)                  # 控制线在视野中的位置，即处于图像的左侧右侧或中间位置
theta_pid = PID(p=0.005, i=0)              # 控制直线角度的偏移

# 初始化函数
def init_setup():
    global sensor, clock                   # 设置为全局变量

    LED(1).on()                            # 打开板载LED灯补光，使巡线环境稳定一些
    LED(2).on()
    LED(3).on()

    sensor.reset()                         # 初始化感光元件
    sensor.set_pixformat(sensor.RGB565)    # 设置图像格式为彩色
    sensor.set_framesize(sensor.QQQVGA)    # 设置图像大小为QQQVGA，80x60 (4,800 pixels) - O(N^2) max = 2,3040,000.
    sensor.skip_frames(10)                 # 跳过10帧使以上设置生效，WARNING: If you use QQVGA it may take seconds
    clock = time.clock()                   # 创建时钟对象
    zl_pan_tilt.main(0, -65)               # 云台倾斜向下，方便查找黑线

# 主函数
def main():
    clock.tick()                                              # 更新FPS帧率时钟
    img = sensor.snapshot().binary([THRESHOLD])               # 拍一张照片并返回图像，图像为二值化格式，即黑线部分显示为白色，非黑色区域显示为黑色
    line = img.get_regression([(100,100)], robust=True)       # 快速线性回归，可以快速返回视野中的一条回归直线，可得到直线的角度、偏移的距离
    if (line):
        rho_err = abs(line.rho()) - img.width() / 2           # 计算直线相对于图像中央偏移的距离
        if line.theta() > 90:                                 # 通过对直线角度的判断来进行坐标的变换，即以直线最远点画竖线来作为x轴的零点位置
            theta_err = line.theta() - 180
        else:
            theta_err = line.theta()
        img.draw_line(line.line(), color=127)                 # 将直线画出来
        print(rho_err,line.magnitude(),rho_err)
        if line.magnitude() > 8:                              # magnitude为霍夫变换后的直线的模，值越大说明效果越好
            #if -40<b_err<40 and -30<t_err<30:
            rho_output = rho_pid.get_pid(rho_err, 1)
            theta_output = theta_pid.get_pid(theta_err, 1)
            output = rho_output + theta_output
            zl_car_run.car_run(int(50+output)*10, int(50-output)*10)  # 开始巡线
        else:
            zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.stop_speed)  # 小车停止
    else:
        zl_car_run.car_run(650,-650)  # 小车原地旋转，找寻黑线
        pass
    #print(clock.fps())

# 程序入口
if __name__ == '__main__':
    init_setup()    # 执行初始化函数
    zl_uart3.init_setup()
    try:
        while 1:
            main()  # 执行主函数
    except:
        zl_pan_tilt.middle()    # 云台复位
        zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.stop_speed)  # 小车停止
