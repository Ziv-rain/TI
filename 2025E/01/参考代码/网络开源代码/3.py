import time
import os
import sys
import math
from media.sensor import *
from media.display import *
from media.media import *
from time import ticks_ms
from machine import FPIOA
from machine import Pin
from machine import Timer
from machine import UART
from machine import TOUCH  # 添加触摸屏支持

sensor = None
blue = 90, 100, -11, 10, -60, 43
black = (0, 96)  # 初始黑色阈值

# 目标点坐标 (160, 116) - 图像中心
TARGET_POINT = (156, 113)

# 全局状态变量
detect_counter = 0            # 矩形识别计数器
lost_counter = 0              # 矩形丢失计数器
min_detect_frames = 2         # 连续检测阈值
min_lost_frames = 5           # 连续丢失阈值
flag_detected = False         # 滤波后的检测状态

# 阈值调节相关变量
threshold_dict = {'black': [black]}  # 存储阈值的字典
adjusting_threshold = False         # 是否正在调节阈值
current_threshold = list(black)     # 当前正在调节的阈值

# 触摸计数器
touch_counter = 0
tp = TOUCH(0)  # 触摸屏对象

def vector_angle_diff(v1, v2):
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    det = v1[0]*v2[1] - v1[1]*v2[0]
    angle = math.atan2(det, dot) * (180 / math.pi)
    return abs(angle)

def get_line_intersection(line1, line2):
    """计算两条直线的交点"""
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    # 计算第一条直线的参数：A1*x + B1*y = C1
    A1 = y2 - y1
    B1 = x1 - x2
    C1 = A1 * x1 + B1 * y1

    # 计算第二条直线的参数：A2*x + B2*y = C2
    A2 = y4 - y3
    B2 = x3 - x4
    C2 = A2 * x3 + B2 * y3

    # 计算行列式
    det = A1 * B2 - A2 * B1

    if det == 0:  # 直线平行
        # 使用备用方法计算中点
        return ((x1 + x3) / 2, (y1 + y3) / 2)
    else:
        # 计算交点
        x = (B2 * C1 - B1 * C2) / det
        y = (A1 * C2 - A2 * C1) / det
        return (x, y)

def sort_corners(corners, center):
    """
    优化角点排序逻辑，确保排序结果更准确
    返回：[左上, 右上, 右下, 左下]
    """
    # 改进1: 使用角度排序前，先找出最上边两个点
    top_points = []
    bottom_points = []

    # 计算所有点的y值
    y_values = [p[1] for p in corners]
    median_y = sum(y_values) / len(y_values)

    # 分为上下两组点
    for p in corners:
        if p[1] < median_y:
            top_points.append(p)
        else:
            bottom_points.append(p)

    # 确保上下两组各有两个点
    if len(top_points) != 2 or len(bottom_points) != 2:
        # 如果分组失败，使用旧方法作为备选
        angles = []
        for point in corners:
            dx = point[0] - center[0]
            dy = point[1] - center[1]
            angle = math.atan2(dy, dx)
            angles.append(angle)

        sorted_indices = sorted(range(len(angles)), key=lambda i: angles[i])
        sorted_corners = [corners[i] for i in sorted_indices]
        return sorted_corners

    # 排序上边的点：按x坐标从左到右
    top_points.sort(key=lambda p: p[0])

    # 排序下边的点：按x坐标从左到右
    bottom_points.sort(key=lambda p: p[0])

    # 左上角是上边左点
    top_left = top_points[0]
    top_right = top_points[1]

    # 左下角和右下角取决于矩形方向
    # 使用向量交叉法确定方向
    vec1 = (top_right[0] - top_left[0], top_right[1] - top_left[1])
    vec2 = (bottom_points[0][0] - top_left[0], bottom_points[0][1] - top_left[1])
    cross = vec1[0] * vec2[1] - vec1[1] * vec2[0]

    if cross > 0:  # 矩形顺时针方向
        bottom_left = bottom_points[0]
        bottom_right = bottom_points[1]
    else:  # 矩形逆时针方向
        bottom_left = bottom_points[1]
        bottom_right = bottom_points[0]

    return [top_left, top_right, bottom_right, bottom_left]

def sending_data(flag, sign_dx_center, dx_center, sign_dy_center, dy_center,
                 base_index, sign_dx_base, dx_base, sign_dy_base, dy_base):
    """
    串口数据包发送函数 (13字节格式)
    数据包格式:
        [0xAA][长度][1-flag][2-sign_dx_center][3-dx_center][4-sign_dy_center][5-dy_center]
        [6-base_index][7-sign_dx_base][8-dx_base][9-sign_dy_base][10-dy_base][校验位]
    校验位 = (前11字节数据的和)的低8位
    """
    global uart2

    # 数据包固定长度: 帧头(1) + 长度(1) + 10个数据 + 校验位(1) = 13字节
    # 长度字段: 表示从长度字节之后到校验位之前的字节数 (12字节)
    PACKET_LENGTH = 0x0D  # 13字节

    # 构建数据包的前部分 (帧头+长度+10个数据)
    packet = [
        0xAA,           # 帧头
        PACKET_LENGTH,  # 包长度
        flag,           # 标志位
        sign_dx_center, # x差符号
        dx_center,      # x差值
        sign_dy_center, # y差符号
        dy_center,      # y差值
        base_index,     # 基准点编号
        sign_dx_base,   # 基准点x差符号
        dx_base,        # 基准点x差值
        sign_dy_base,   # 基准点y差符号
        dy_base         # 基准点y差值
    ]

    # 计算校验位（前11个字节和的后8位/低8位）
    checksum = sum(packet) & 0xFF

    # 通过串口发送完整数据包 (13字节)
    uart2.write(bytes(packet) + bytes([checksum]))

def draw_threshold_ui(img, threshold_min, threshold_max):
    """绘制阈值调节界面"""
    # 清除屏幕
    img.draw_rectangle(0, 0, img.width(), img.height(), color=(255, 255, 255), fill=True)

    # 绘制标题
    img.draw_string_advanced(280, 20, 40, "阈值调节", color=(0, 0, 0))

    # 绘制阈值显示
    img.draw_string_advanced(240, 70, 35, f"Min: {threshold_min}", color=(0, 0, 0))
    img.draw_string_advanced(400, 70, 35, f"Max: {threshold_max}", color=(0, 0, 0))

    # 设计更大的按钮 (120×120像素)，两侧放置
    button_width = 120
    button_height = 120
    button_spacing = 20

    # Min按钮放在左侧
    # Min减少按钮 (上方)
    img.draw_rectangle(40, 150, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(65, 200, 60, "-", color=(0, 0, 0))

    # Min增加按钮 (下方)
    img.draw_rectangle(40, 280 + button_spacing, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(65, 330, 60, "+", color=(0, 0, 0))

    # Max按钮放在右侧
    # Max减少按钮 (上方)
    img.draw_rectangle(640, 150, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(665, 200, 60, "-", color=(0, 0, 0))

    # Max增加按钮 (下方)
    img.draw_rectangle(640, 280 + button_spacing, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(665, 330, 60, "+", color=(0, 0, 0))

    # 在中央显示当前摄像头画面
    snapshot = sensor.snapshot(chn=CAM_CHN_ID_0)
    if snapshot:
        # 二值化处理
        binary_img = snapshot.to_grayscale(copy=True)
        binary_img = binary_img.binary([(threshold_min, threshold_max)])

        x_pos = (800 - 320) // 2
        y_pos = 150
        img.draw_image(binary_img, x_pos, y_pos)

    # 底部按钮 - 更大尺寸 (160×80像素)
    button_width = 160
    button_height = 80
    img.draw_rectangle(100, 400, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(140, 430, 35, "返回", color=(0, 0, 0))

    img.draw_rectangle(540, 400, button_width, button_height, color=(200, 200, 200), fill=True)
    img.draw_string_advanced(580, 430, 35, "保存", color=(0, 0, 0))

def handle_threshold_adjustment():
    """处理阈值调节模式"""
    global adjusting_threshold, current_threshold, threshold_dict

    # 创建界面图像
    ui_img = image.Image(800, 480, image.RGB565)

    # 显示初始阈值
    min_val = current_threshold[0]
    max_val = current_threshold[1]

    while adjusting_threshold:
        # 绘制UI界面
        draw_threshold_ui(ui_img, min_val, max_val)

        # 显示UI
        ui_img.compress_for_ide()
        Display.show_image(ui_img, 0, 0)

        # 处理触摸事件
        points = tp.read()
        if len(points) > 0:
            touch_x = points[0].x
            touch_y = points[0].y

            # 检测Min按钮
            # Min减按钮 (左上方)
            if 40 <= touch_x <= 160 and 150 <= touch_y <= 270:
                min_val = max(0, min_val - 1)
                time.sleep_ms(200)  # 防止连续点击

            # Min加按钮 (左下方)
            elif 40 <= touch_x <= 160 and 300 <= touch_y <= 420:
                min_val = min(255, min_val + 1)
                time.sleep_ms(200)  # 防止连续点击

            # 检测Max按钮
            # Max减按钮 (右上方)
            elif 640 <= touch_x <= 760 and 150 <= touch_y <= 270:
                max_val = max(0, max_val - 1)
                time.sleep_ms(200)  # 防止连续点击

            # Max加按钮 (右下方)
            elif 640 <= touch_x <= 760 and 300 <= touch_y <= 420:
                max_val = min(255, max_val + 1)
                time.sleep_ms(200)  # 防止连续点击

            # 返回按钮
            elif 100 <= touch_x <= 260 and 400 <= touch_y <= 480:
                adjusting_threshold = False

            # 保存按钮
            elif 540 <= touch_x <= 700 and 400 <= touch_y <= 480:
                # 保存当前阈值
                current_threshold[0] = min_val
                current_threshold[1] = max_val
                threshold_dict['black'] = [(min_val, max_val)]
                # 更新全局变量
                global black
                black = (min_val, max_val)
                adjusting_threshold = False
                # 短暂显示保存成功提示
                for _ in range(3):
                    draw_threshold_ui(ui_img, min_val, max_val)
                    ui_img.draw_rectangle(200, 200, 400, 60, color=(150, 150, 150), fill=True)
                    ui_img.draw_string_advanced(300, 220, 35, "保存成功!", color=(0, 255, 0))
                    ui_img.compress_for_ide()
                    Display.show_image(ui_img, 0, 0)
                    time.sleep_ms(500)
                break

try:
    flag_key = 0
    print("camera_test")
    fpioa = FPIOA()
    fpioa.set_function(53, FPIOA.GPIO53)
    fpioa.set_function(11, FPIOA.UART2_TXD)
    fpioa.set_function(12, FPIOA.UART2_RXD)

    uart2 = UART(UART.UART2,115200)

    key = Pin(53, Pin.IN, Pin.PULL_DOWN)
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(Sensor.QVGA)
    sensor.set_pixformat(Sensor.RGB565)
    time.sleep(1)

    Display.init(Display.ST7701, width=800, height=480, to_ide=True)
    MediaManager.init()
    sensor.run()
    clock = time.clock()

    # 用于存储上一帧的矩形信息
    prev_min_corners = None
    prev_has_rect = False  # 用于跟踪上一帧是否有检测到矩形

    while True:
        if key.value() == 1:
            while key.value() == 1:
                pass
            flag_key = (flag_key + 1) % 2
            time.sleep_ms(20)  # 释放后延时防止连按

        # 添加阈值调节模式触发
        points = tp.read()
        if len(points) > 0:
            touch_counter += 1
            if touch_counter > 20:  # 长按触发
                adjusting_threshold = True
                # 使用当前阈值开始调整
                current_threshold = list(black)
                handle_threshold_adjustment()
                touch_counter = 0
        else:
            touch_counter = max(0, touch_counter - 1)

        clock.tick()
        os.exitpoint()

        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        img_binary = img.to_grayscale(copy=True)
        img_binary = img_binary.binary([black])
        img_binary.dilate(2)
        rects = img_binary.find_rects(threshold=1500)

        # 初始化最小矩形变量
        min_rect = None
        min_area = float('inf')  # 初始化为无穷大
        min_corners = None
        min_black_ratio = 0
        survivors = []  # 幸存下来的矩形

        if rects is not None:
            for rect in rects:
                corners = rect.corners()
                # 确保四边形有4个顶点
                if len(corners) != 4:
                    continue

                # 计算当前矩形的面积（使用像素数量）
                current_area = rect.w() * rect.h()
                if current_area < 1500:  # 确保矩形面积大于5000像素
                    continue

                # 计算所有内角误差
                angles = []
                max_angle_error = 0
                for i in range(4):
                    # 获取三个连续点 (前一个点-当前点-后一个点)
                    p0 = corners[(i-1) % 4]
                    p1 = corners[i]
                    p2 = corners[(i+1) % 4]

                    # 创建两个向量
                    vec1 = (p0[0]-p1[0], p0[1]-p1[1])
                    vec2 = (p2[0]-p1[0], p2[1]-p1[1])

                    # 计算角度差(理想应为180°-90°=90°差异)
                    angle_diff = vector_angle_diff(vec1, vec2)
                    angle_error = abs(angle_diff - 90)  # 计算与直角的偏差
                    angles.append(angle_error)
                    if angle_error > max_angle_error:
                        max_angle_error = angle_error

                # 计算平均偏差
                avg_angle_error = sum(angles) / len(angles)

                # 角度偏差检查 - 适当放宽条件提高灵敏度
                if max_angle_error > 45 or avg_angle_error > 30:
                    continue

                # ========== 中心区域滤波 ==========
                # 计算矩形中心点
                center = get_line_intersection([corners[0], corners[2]], [corners[1], corners[3]])
                center_x, center_y = int(center[0]), int(center[1])

                # 计算中心矩形区域（整个矩形的中心1/2区域）
                center_rect_x_start = max(0, center_x - rect.w() // 4)
                center_rect_x_end = min(img.width() - 1, center_x + rect.w() // 4)
                center_rect_y_start = max(0, center_y - rect.h() // 4)
                center_rect_y_end = min(img.height() - 1, center_y + rect.h() // 4)

                # 检查区域内有效像素数量
                valid_pixels = 0
                total_pixels = 0

                # 使用6像素步长遍历中心区域
                step_size = 7
                for y in range(center_rect_y_start, center_rect_y_end, step_size):
                    for x in range(center_rect_x_start, center_rect_x_end, step_size):
                        pixel_value = img_binary.get_pixel(x, y)
                        # 检查像素值是否为0（黑色）
                        if isinstance(pixel_value, tuple):
                            pixel_value = pixel_value[0]  # 如果是元组则取第一个元素
                        if pixel_value == 0:  # 黑色像素
                            valid_pixels += 1
                        total_pixels += 1

                # 计算黑色像素比例
                if total_pixels > 0:
                    black_ratio = valid_pixels / total_pixels
                else:
                    black_ratio = 0.0

                # 如果黑色像素不足20%，跳过该矩形
                if black_ratio < 0.4:
                    continue

                # 将该矩形加入幸存者列表
                survivors.append((rect, corners, black_ratio, max_angle_error, avg_angle_error))

                # 更新最小矩形（按面积排序）
                if current_area < min_area:
                    min_area = current_area
                    min_rect = rect
                    min_corners = corners
                    min_black_ratio = black_ratio

        # 从幸存者中选择最小面积矩形作为最终结果
        if len(survivors) > 0:
            min_area = float('inf')
            min_rect = None
            min_corners = None
            min_black_ratio = 0
            for rect, corners, black_ratio, max_angle_error, avg_angle_error in survivors:
                area = rect.w() * rect.h()
                if area < min_area:
                    min_area = area
                    min_rect = rect
                    min_corners = corners
                    min_black_ratio = black_ratio
        else:
            min_rect = None
            min_corners = None

        # 标记当前帧是否有检测到矩形
        current_has_rect = min_corners is not None

        # 如果没有检测到新的最小矩形，尝试使用上一帧的矩形
        if not current_has_rect and prev_min_corners is not None:
            min_corners = prev_min_corners
            use_prev = True
        else:
            use_prev = False

        # 检测标志滤波处理 - 优化为更灵敏的滤波
        if current_has_rect:
            # 新检测到矩形
            if not flag_detected:
                detect_counter += 1
                if detect_counter >= min_detect_frames:
                    flag_detected = True
                    detect_counter = 0
            else:
                lost_counter = 0  # 持续检测中重置丢失计数
        else:
            # 丢失矩形
            if flag_detected:
                lost_counter += 1
                if lost_counter >= min_lost_frames:
                    flag_detected = False
                    lost_counter = 0
            else:
                detect_counter = 0  # 持续丢失中重置检测计数

        # 初始化串口数据变量
        flag_byte = 0xBB if flag_detected else 0xCC
        sign_dx_center, dx_center_val, sign_dy_center, dy_center_val = 0, 0, 0, 0

        # 只处理最小矩形
        if min_corners is not None and flag_detected:
            # 如果是新的矩形（非上一帧的），更新缓存
            if not use_prev:
                prev_min_corners = min_corners

            # 绘制验证通过的矩形 (绿线) - 如果是当前帧检测到的
            if not use_prev:
                img.draw_line(min_corners[0][0], min_corners[0][1], min_corners[1][0], min_corners[1][1], color=(0, 255, 0), thickness=2)
                img.draw_line(min_corners[1][0], min_corners[1][1], min_corners[2][0], min_corners[2][1], color=(0, 255, 0), thickness=2)
                img.draw_line(min_corners[2][0], min_corners[2][1], min_corners[3][0], min_corners[3][1], color=(0, 255, 0), thickness=2)
                img.draw_line(min_corners[3][0], min_corners[3][1], min_corners[0][0], min_corners[0][1], color=(0, 255, 0), thickness=2)

            # ============ 使用对角线交点获取中心点 ============
            diagonal1 = [min_corners[0], min_corners[2]]
            diagonal2 = [min_corners[1], min_corners[3]]
            center = get_line_intersection(diagonal1, diagonal2)
            center_x, center_y = int(center[0]), int(center[1])

            # 在中心位置绘制黄色圆圈 (半径2像素)
            img.draw_circle(center_x, center_y, 2, color=(255, 255, 0), thickness=1)

            # 计算中心点差值
            dx_center = TARGET_POINT[0] - center_x
            dy_center = TARGET_POINT[1] - center_y

            # 处理中心点差值数据
            if dx_center < 0:
                sign_dx_center = 1
                dx_center_val = min(255, int(abs(dx_center)))
            else:
                sign_dx_center = 0
                dx_center_val = min(255, int(abs(dx_center)))

            if dy_center < 0:
                sign_dy_center = 1
                dy_center_val = min(255, int(abs(dy_center)))
            else:
                sign_dy_center = 0
                dy_center_val = min(255, int(abs(dy_center)))

        # 如果没有检测到矩形，重置缓存
        if min_corners is None:
            prev_min_corners = None

        # 更新上一帧状态
        prev_has_rect = current_has_rect

        # 显示状态信息
#        img.draw_circle(TARGET_POINT[0], TARGET_POINT[1], 3, color=(255, 0, 255), thickness=1)
        img.draw_string_advanced(10, 10, 15, "fps: {:.1f}".format(clock.fps()), color=(255, 0, 0))
        img.draw_string_advanced(10, 30, 15, "status: {}".format("Tracking" if flag_detected else "Lost"),
                                color=(0, 255, 0) if flag_detected else (255, 0, 0))
        img.draw_string_advanced(10, 50, 15, "threshold: {}".format(black), color=(0, 0, 255))

        #发送串口数据（基准点相关数据全部设为0）
        sending_data(
            flag_byte,
            sign_dx_center,
            dx_center_val,
            sign_dy_center,
            dy_center_val,
            0,   # base_index
            0,   # sign_dx_base
            0,   # dx_base_val
            0,   # sign_dy_base
            0    # dy_base_val
        )

        img.compressed_for_ide()
        Display.show_image(img, x=(800-320)//2, y=(480-240)//2)

finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
