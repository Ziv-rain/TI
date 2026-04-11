import sensor, image, time

from pid import PID
from pyb import Servo


# 初始化函数
def init_setup():
    global pan_servo, tilt_servo, pan_pid, tilt_pid, sensor, clock, face_cascade
    pan_servo = Servo(1)                         # 实例化云台靠下的舵机
    tilt_servo = Servo(2)                        # 实例化云台靠上的舵机

    pan_servo.calibration(500,2500,1500)         # 设置舵机脉冲范围为500-2500，中心位置为1500
    tilt_servo.calibration(500,2500,1500)        # 设置舵机脉冲范围为500-2500，中心位置为1500

    #pan_pid = PID(p=0.07, i=0, imax=90)          # 脱机运行或者禁用图像传输，使用这个PID
    #tilt_pid = PID(p=0.05, i=0, imax=90)         # 脱机运行或者禁用图像传输，使用这个PID
    pan_pid = PID(p=0.10, i=0,d=0.003, imax=90)           # 在线调试使用这个PID
    tilt_pid = PID(p=0.10, i=0,d=0.006, imax=90)          # 在线调试使用这个PID

    sensor.reset()                               # 初始化感光元件
    sensor.set_contrast(3)                       # 对比度
    sensor.set_gainceiling(16)                   # 自动增益
    sensor.set_pixformat(sensor.GRAYSCALE)       # 图像格式设置为灰度
    sensor.set_framesize(sensor.HQVGA)           # 图像大小设置为HQVGA，即240x160
    sensor.skip_frames(10)                       # 跳过10帧，使以上设置生效
    sensor.set_auto_whitebal(False)              # 关闭白平衡
    clock = time.clock()                         # 创建时钟对象
    face_cascade = image.HaarCascade("frontalface", stages=25)

# 舵机回归中位
def middle():
    pan_servo.angle(0, 1000)                     # 舵机在1秒内转到0度位置
    tilt_servo.angle(0, 1000)                    # 舵机在1秒内转到0度位置
    time.sleep(1)                                # 延时1秒

# 查找识别到的目标颜色区域中最大区域的函数
def find_max(blobs):
    max_size = 0
    for blob in blobs:
        if blob[2] * blob[3] > max_size:
            max_blob = blob
            max_size = blob[2] * blob[3]
    return max_blob

# 主函数
def main():
    while 1:
        clock.tick()                             # 更新FPS帧率时钟
        img = sensor.snapshot()                  # 拍一张照片并返回图像

        faces = img.find_features(face_cascade, threshold=0.75, scale=1.25)
        if faces:
            face = find_max(faces)
            cx = int(face[0] + face[2] / 2)
            cy = int(face[1] + face[3] / 2)
            pan_error = cx - img.width() / 2
            tilt_error = cy - img.height() / 2

            #print("tilt_error: ", tilt_error)

            img.draw_rectangle(face)             # 将最大的目标区域框出来
            img.draw_cross(cx, cy)               # 在目标区域的中心点处画十字

            pan_output = pan_pid.get_pid(pan_error, 1) / 2
            tilt_output = tilt_pid.get_pid(tilt_error, 1) / 2
            #print("tilt_output", tilt_output)
            pan_servo.angle(pan_servo.angle() - pan_output)
            tilt_servo.angle(tilt_servo.angle() - tilt_output)

            # 异常判断，定义舵机极限位置
            if pan_servo.angle() > 90:
                pan_servo.angle(90)
            if pan_servo.angle() < -90:
                pan_servo.angle(-90)
            if tilt_servo.angle() > 45:
                tilt_servo.angle(45)
            if tilt_servo.angle() < -60:
                tilt_servo.angle(-60)

# 程序入口
if __name__ == '__main__':
    init_setup()    # 执行初始化函数
    try:
        main()      # 执行主函数
    finally:
        middle()    # 程序结束时使云台舵机复位
