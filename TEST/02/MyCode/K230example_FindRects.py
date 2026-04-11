'''
实验名称:矩形检测 + 云台控制
实验平台:01Studio CanMV K230
教程:wiki.01studio.cc
说明:推荐使用320x240以下分辨率，分辨率过大会导致帧率下降。
'''

import time
import gc
from machine import PWM, FPIOA

from media.sensor import *
from media.display import *
from media.media import *

# ===== 参数区 =====
FRAME_W = 320  # 摄像头传感器分辨率宽度
FRAME_H = 240  # 摄像头传感器分辨率高度
RECT_THRESHOLD = 20000  # 矩形检测的阈值参数
MIN_W = 50  # 识别矩形最小宽
MIN_H = 50  # 识别矩形最小高
LCD_W = 800  # LCD显示分辨率宽度
LCD_H = 480  # LCD显示分辨率高度
PWM_FREQ = 50  # 舵机PWM频率

# 本地PWM分配
SERVO_X_PWM_CH = 0   # PWM0 -> GPIO42（X轴：360°连续旋转舵机）
SERVO_Y_PWM_CH = 1   # PWM1 -> GPIO43（Y轴：180°位置舵机）
SERVO_X_GPIO = 42
SERVO_Y_GPIO = 43

# 舵机脉宽参数（单位：ns）
SERVO_MIN_NS = 500000
SERVO_MID_NS = 1500000
SERVO_MAX_NS = 2500000

# Y轴舵机限位（角度制，-90~90）
TILT_MIN_ANGLE = -85
TILT_MAX_ANGLE = 85
TILT_CENTER_ANGLE = 0  # Y轴机械中位角

# 丢目标时X轴连续旋转舵机回零速
LOST_TARGET_X_SPEED = 0


def clamp(value, min_value, max_value):
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def angle_to_duty_ns(angle):
    angle = clamp(angle, -90, 90)
    return int((angle + 90) / 180 * (SERVO_MAX_NS - SERVO_MIN_NS) + SERVO_MIN_NS)


def init_servos():
    fpioa = FPIOA()
    fpioa.set_function(SERVO_X_GPIO, FPIOA.PWM0)
    fpioa.set_function(SERVO_Y_GPIO, FPIOA.PWM1)

    servo_x = PWM(SERVO_X_PWM_CH, freq=PWM_FREQ, duty_ns=0)
    servo_y = PWM(SERVO_Y_PWM_CH, freq=PWM_FREQ, duty_ns=0)

    servo_x.duty_ns(SERVO_MID_NS)  # 360舵机停转
    servo_y.duty_ns(SERVO_MID_NS)  # 180舵机回中
    return servo_x, servo_y


def set_servo360_speed(servo, speed_cmd):
    speed_cmd = clamp(speed_cmd, -90, 90)
    servo.duty_ns(angle_to_duty_ns(speed_cmd))


def set_servo180_angle(servo, angle):
    angle = clamp(angle, TILT_MIN_ANGLE, TILT_MAX_ANGLE)
    servo.duty_ns(angle_to_duty_ns(angle))
    return angle


def init_camera_and_display():
    """
    初始化摄像头传感器和显示设备，并启动摄像头运行。

    该函数完成以下操作：
    - 创建并配置图像传感器（分辨率、像素格式等）
    - 初始化显示设备（使用 ST7701 驱动）
    - 初始化媒体管理器
    - 启动传感器采集

    返回值:
        sensor (Sensor): 已初始化并开始运行的图像传感器对象
    """
    sensor = Sensor(width=1280, height=960)
    sensor.reset()
    sensor.set_framesize(width=FRAME_W, height=FRAME_H)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, to_ide=True)
    MediaManager.init()
    sensor.run()
    return sensor


def find_largest_rect(img, threshold=RECT_THRESHOLD, min_w=MIN_W, min_h=MIN_H):
    """
    在图像中查找满足尺寸条件的最大矩形区域。

    该函数遍历图像中检测到的所有矩形，筛选出宽度和高度均大于指定最小值的矩形，
    并返回其中面积最大的矩形的相关信息。

    参数:
        img: 输入图像对象，需支持 find_rects() 方法用于检测矩形。
        threshold (int): 矩形检测的阈值参数，默认为全局常量 RECT_THRESHOLD。
        min_w (int): 矩形的最小宽度阈值，默认为全局常量 MIN_W。
        min_h (int): 矩形的最小高度阈值，默认为全局常量 MIN_H。

    返回值:
        tuple: 包含三个元素的元组：
            - best_rect: 最大面积矩形的边界框（格式通常为 (x, y, w, h)），若无符合条件的矩形则为 None。
            - best_corners: 最大面积矩形的四个角点坐标列表，若无符合条件的矩形则为 None。
            - max_area: 最大面积矩形的面积值，若无符合条件的矩形则为 0。
    """
    max_area = 0
    best_rect = None
    best_corners = None

    # 遍历图像中所有检测到的矩形，筛选出满足最小宽高要求且面积最大的矩形
    for r in img.find_rects(threshold=threshold):
        if r.w() > min_w and r.h() > min_h:
            area = r.w() * r.h()
            if area > max_area:
                max_area = area
                best_rect = r.rect()
                best_corners = r.corners()

    return best_rect, best_corners, max_area


def draw_rect_and_center(img, rect, corners):
    """
    在图像上绘制矩形、角点和中心十字标记，并返回中心坐标。

    该函数首先在图像上绘制一个红色矩形，然后在给定的四个角点位置绘制绿色圆形，
    最后计算并绘制黄色十字标记表示四个角点的几何中心，并返回该中心的整数坐标。

    参数:
        img: 图像对象，支持 draw_rectangle、draw_circle 和 draw_cross 方法。
        rect: 矩形区域，格式通常为 (x, y, w, h)，用于绘制外框矩形。
        corners: 包含四个角点坐标的列表或元组，每个角点为 (x, y) 格式。

    返回值:
        tuple: 中心点的整数坐标 (center_x, center_y)。
    """
    img.draw_rectangle(rect, color=(255, 0, 0), thickness=2)
    for p in corners:
        img.draw_circle(p[0], p[1], 5, color=(0, 255, 0))

    # 计算四个角点的平均坐标作为中心点
    center_x = (corners[0][0] + corners[1][0] + corners[2][0] + corners[3][0]) / 4
    center_y = (corners[0][1] + corners[1][1] + corners[2][1] + corners[3][1]) / 4

    img.draw_cross(int(center_x),
                   int(center_y),
                   color=(255, 255, 0),
                   size=10,
                   thickness=2)
    return int(center_x), int(center_y)


class PID:
    def __init__(self, kp, ki, kd, out_min=-100, out_max=100, i_min=-50, i_max=50):
        """
        初始化PID控制器参数和状态变量。
        
        参数:
            kp (float): 比例增益系数。
            ki (float): 积分增益系数。
            kd (float): 微分增益系数。
            out_min (float, 可选): 控制器输出的最小限制值，默认为-100。
            out_max (float, 可选): 控制器输出的最大限制值，默认为100。
            i_min (float, 可选): 积分项的最小限制值，默认为-50。
            i_max (float, 可选): 积分项的最大限制值，默认为50。
            
        无返回值。
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.out_min = out_min
        self.out_max = out_max
        self.i_min = i_min
        self.i_max = i_max
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, setpoint, measurement, dt):
        """
        执行PID控制器的一次更新计算，返回控制输出值。
        
        该函数基于当前设定值(setpoint)与实际测量值(measurement)之间的误差，
        结合比例、积分、微分三项计算控制输出，并对积分项和最终输出进行限幅处理。
        
        参数:
            setpoint (float): 目标设定值，即期望系统达到的状态。
            measurement (float): 当前系统的实际测量值。
            dt (float): 自上次调用以来的时间间隔（秒），必须为正数。
            
        返回:
            float: 经过PID计算并限幅后的控制输出值。若dt <= 0，则返回0.0。
        """
        if dt <= 0:
            return 0.0
        error = setpoint - measurement
        self.integral += error * dt
        # 对积分项进行限幅，防止积分饱和
        if self.integral > self.i_max:
            self.integral = self.i_max
        elif self.integral < self.i_min:
            self.integral = self.i_min

        derivative = (error - self.prev_error) / dt
        out = self.kp * error + self.ki * self.integral + self.kd * derivative

        # 对最终输出进行限幅，确保控制信号在有效范围内
        if out > self.out_max:
            out = self.out_max
        elif out < self.out_min:
            out = self.out_min

        self.prev_error = error
        return out


class IncrementalPID:
    def __init__(self, kp, ki, kd, out_min=-100, out_max=100):
        """
        初始化PID控制器参数及内部状态。
        
        参数:
            kp (float): 比例增益系数。
            ki (float): 积分增益系数。
            kd (float): 微分增益系数。
            out_min (float, optional): 控制器输出的最小值限制，默认为-100。
            out_max (float, optional): 控制器输出的最大值限制，默认为100。
            
        该构造函数初始化PID控制器的比例、积分、微分系数，并设置输出限幅范围。
        同时将历史误差和初始输出值重置为零，为后续控制计算做准备。
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.out_min = out_min
        self.out_max = out_max
        self.error_1 = 0.0
        self.error_2 = 0.0
        self.output = 0.0

    def reset(self, output=0.0):
        """
        重置控制器状态，将输出值初始化为指定值，并清零历史误差。
        
        参数:
            output (float): 初始输出值，默认为 0.0。该值会被限制在控制器的输出范围内。
        """
        self.output = clamp(output, self.out_min, self.out_max)
        self.error_1 = 0.0
        self.error_2 = 0.0

    def prime(self, error):
        """
        初始化或设置对象的误差值。
        
        该函数将传入的 error 值同时赋给实例变量 error_1 和 error_2，
        用于后续计算或状态维护。

        参数:
            error (任意类型): 用于初始化 error_1 和 error_2 的值。

        返回值:
            无。
        """
        self.error_1 = error
        self.error_2 = error

    def update(self, setpoint, measurement, dt):
        """
        使用增量式PID算法计算并更新控制器输出。

        该方法基于当前设定值、测量值和采样时间，采用位置式PID的增量形式进行计算，
        并对输出进行限幅处理。同时更新历史误差用于下一次微分项计算。

        参数:
            setpoint (float): 目标设定值，即期望系统达到的值。
            measurement (float): 当前实际测量值，即系统的反馈值。
            dt (float): 自上次调用以来的时间间隔（采样周期），单位通常为秒。

        返回值:
            float: 经过限幅后的控制器输出值。
        """
        if dt <= 0:
            return self.output

        # 计算当前误差及增量式PID控制量
        error = setpoint - measurement
        delta_u = self.kp * (error - self.error_1) + \
            self.ki * error * dt + \
            self.kd * (error - 2 * self.error_1 + self.error_2) / dt

        # 更新输出并进行限幅
        self.output += delta_u
        self.output = clamp(self.output, self.out_min, self.out_max)

        # 更新历史误差记录，用于下次微分项计算
        self.error_2 = self.error_1
        self.error_1 = error
        return self.output


def main():
    # 初始化视觉链路：摄像头 + 显示
    sensor = init_camera_and_display()

    # 初始化本地PWM舵机对象（X轴360°连续旋转，Y轴180°位置舵机）
    servo_x, servo_y = init_servos()

    # 帧率统计时钟
    clock = time.clock()

    # X轴采用增量式PID，输出作为连续旋转舵机的速度命令
    pid_x = IncrementalPID(kp=0.35, ki=0.00, kd=0.08, out_min=-50, out_max=50)
    # Y轴采用位置式PID：输出作为相对中位角的偏移量（单位：角度）
    pid_y = PID(kp=0.35, ki=0.00, kd=0.08, out_min=-45, out_max=45)

    # 视觉目标：屏幕中心（让矩形中心尽量对齐该点）
    target_x = FRAME_W / 2
    target_y = FRAME_H / 2

    # 时间基准：用于计算PID的dt
    last_ms = time.ticks_ms()

    # 目标是否丢失标记：用于重捕获时做状态平滑
    target_lost = True

    # 初始化控制量，避免未定义
    pan_out = 0
    tilt_out = 0

    # Y轴当前角度命令（以机械中位角为初值）
    tilt_angle = TILT_CENTER_ANGLE

    while True:
        # 更新帧率计数并采集一帧图像
        clock.tick()
        img = sensor.snapshot()  # 获取当前帧图像

        # 每帧都更新时间，避免目标丢失后再次识别时dt突变
        now_ms = time.ticks_ms()
        dt = time.ticks_diff(now_ms, last_ms) / 1000.0
        last_ms = now_ms

        # 对dt做限幅，抑制异常采样周期导致的控制抖动
        dt = clamp(dt, 0.001, 0.05)

        # 检测当前帧中最大有效矩形
        rect, corners, area = find_largest_rect(img)

        # 仅在检测到矩形时更新中心点和PID
        if rect is not None:
            # 绘制检测结果并得到矩形中心坐标
            center_x, center_y = draw_rect_and_center(img, rect, corners)

            # 当目标丢失后重新捕获时，重置PID控制器状态以平滑恢复跟踪：
            # - 为X轴PID设置初始输出速度，并预设误差值以避免突变；
            # - 重置Y轴PID的积分项并保存当前误差作为上一次误差，确保控制连续性。
            if target_lost:
                pid_x.reset(LOST_TARGET_X_SPEED)
                pid_x.prime(target_x - center_x)
                pid_y.prev_error = target_y - center_y
                pid_y.integral = 0
                target_lost = False

            # 计算X/Y轴控制输出
            pan_out = pid_x.update(target_x, center_x, dt)
            tilt_out = pid_y.update(target_y, center_y, dt)

            # X轴（360°连续旋转舵机）：输出为速度命令
            set_servo360_speed(servo_x, pan_out)

            # Y轴（180°位置舵机）：位置式PID，直接得到目标角度并限幅下发
            tilt_angle = TILT_CENTER_ANGLE + tilt_out
            tilt_angle = set_servo180_angle(servo_y, tilt_angle)

        else:
            # 目标丢失：标记丢失并将X轴回到安全速度，Y轴保持当前角度
            target_lost = True
            pid_x.reset(LOST_TARGET_X_SPEED)
            pid_y.integral = 0
            pan_out = LOST_TARGET_X_SPEED
            set_servo360_speed(servo_x, pan_out)
            tilt_angle = set_servo180_angle(servo_y, tilt_angle)
            
        # 将当前处理结果显示到屏幕中央
        Display.show_image(img,
                           x=round((LCD_W - sensor.width()) / 2),
                           y=round((LCD_H - sensor.height()) / 2))
      
        # print(clock.fps())
        # print("Free Mem:", gc.mem_free())


if __name__ == "__main__":
    main()
