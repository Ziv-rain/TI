import math
import sensor
import time

try:
    from pyb import UART
except ImportError:
    UART = None


# =========================
# 可调参数（先在现场标定这些参数）
# =========================

# 灰度阈值：用于提取黑色目标（值越小越黑）
BLACK_THRESHOLD = (0, 55)

# 候选区域最小像素和面积，过滤小噪声
PIXELS_THRESHOLD = 200
AREA_THRESHOLD = 200

# 几何筛选：竖直矩形应“高明显大于宽”
MIN_WIDTH = 6
MIN_HEIGHT = 16
MIN_ASPECT_RATIO = 1.8
MIN_DENSITY = 0.8
MIN_ELONGATION = 0.45

# 竖直角度容差（度）：误差越小越严格
VERTICAL_TOLERANCE_DEG = 1.0

# ROI分割：只关注下半屏（从画面高度的50%开始）
ROI_Y_START_RATIO = 0.5
SHOW_ROI_BOX = True
DETECTION_ROI = None

# 计数去重参数
# 连续丢失这么多帧后，才允许下一次计数。
COUNT_LOST_RESET_FRAMES = 10
# 每次计数后进入冷却，避免同一目标短时抖动重复计数。
COUNT_COOLDOWN_FRAMES = 8

# 串口打印控制
# True: 仅打印计数变化；False: 额外按间隔打印状态。
PRINT_COUNT_ONLY = True
STATUS_PRINT_INTERVAL = 20

# 串口协议配置（视觉端 -> 电控端）
UART_PORT = 1
UART_BAUDRATE = 115200
FRAME_HEADER_1 = 0xAA
FRAME_HEADER_2 = 0x55
FRAME_LEN = 0x00

# 命令字定义
CMD_REVERSE_PARK = 0x01
CMD_SIDE_PARK = 0x02

# 指令触发阈值
TRIGGER_COUNT_CMD01 = 3
TRIGGER_COUNT_CMD02 = 6

# 发送01后暂停识别时长（毫秒，可随时调整）
PAUSE_AFTER_CMD01_MS = 3000


def init_camera():
    """初始化OpenMV相机参数。"""
    global DETECTION_ROI

    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QQVGA)
    sensor.set_auto_gain(False)
    sensor.skip_frames(time=2000)

    # 根据当前分辨率动态生成下半屏ROI。
    width = sensor.width()
    height = sensor.height()
    roi_y = int(height * ROI_Y_START_RATIO)
    DETECTION_ROI = (0, roi_y, width, height - roi_y)


def init_uart():
    """初始化UART3串口。"""
    if UART is None:
        print("UART_INIT_FAIL")
        return None
    return UART(UART_PORT, UART_BAUDRATE, bits=8, parity=None, stop=1)


def build_uart_frame(cmd):
    """构建固定5字节协议帧：AA 55 CMD 00 CHK。"""
    checksum = (FRAME_HEADER_1 + FRAME_HEADER_2 + cmd + FRAME_LEN) & 0xFF
    return bytes((FRAME_HEADER_1, FRAME_HEADER_2, cmd, FRAME_LEN, checksum))


def send_uart_command(uart, cmd):
    """发送协议帧并打印发送内容。"""
    frame = build_uart_frame(cmd)
    if uart is not None:
        uart.write(frame)
    print("TX=%02X %02X %02X %02X %02X" % (frame[0], frame[1], frame[2], frame[3], frame[4]))


def calc_vertical_error_deg(blob):
    """基于主轴线计算与竖直方向的夹角误差。"""
    x1, y1, x2, y2 = blob.major_axis_line()
    dx = x2 - x1
    dy = y2 - y1

    # 主轴长度过小会导致角度不稳定。
    if (dx == 0) and (dy == 0):
        return 90.0, 0.0

    angle_deg = abs(math.degrees(math.atan2(dy, dx)))

    # 规约到[0, 90]，便于统一比较。
    if angle_deg > 90.0:
        angle_deg = 180.0 - angle_deg

    vertical_error = abs(90.0 - angle_deg)
    return vertical_error, angle_deg


def check_vertical_black_rect(blob):
    """判断候选目标是否满足“黑色竖直矩形”条件。"""
    w = blob.w()
    h = blob.h()

    if (w < MIN_WIDTH) or (h < MIN_HEIGHT):
        return False, 0.0, 0.0, 0.0

    aspect_ratio = h / float(w)
    if aspect_ratio < MIN_ASPECT_RATIO:
        return False, aspect_ratio, 0.0, 0.0

    density = blob.density()
    if density < MIN_DENSITY:
        return False, aspect_ratio, 0.0, 0.0

    # 拉伸度太低时，主轴角度不稳定。
    elongation = blob.elongation()
    if elongation < MIN_ELONGATION:
        return False, aspect_ratio, 0.0, 0.0

    vertical_error, angle_deg = calc_vertical_error_deg(blob)
    if vertical_error > VERTICAL_TOLERANCE_DEG:
        return False, aspect_ratio, vertical_error, angle_deg

    return True, aspect_ratio, vertical_error, angle_deg


def main_loop():
    clock = time.clock()
    frame_id = 0
    uart = init_uart()

    # 计数与去重状态
    target_count = 0
    count_latch = False
    lost_frames = 0
    cooldown_frames = 0

    # 命令触发状态（确保每条命令只发送一次）
    cmd01_sent = False
    cmd02_sent = False

    # 识别暂停状态（发送01后启用）
    pause_until_ms = 0
    is_paused = False

    while True:
        clock.tick()
        img = sensor.snapshot()
        frame_id += 1

        if SHOW_ROI_BOX:
            img.draw_rectangle(DETECTION_ROI, color=180, thickness=1)

        # 发送01后暂停识别，到时自动恢复。
        if is_paused:
            if time.ticks_diff(pause_until_ms, time.ticks_ms()) > 0:
                continue
            is_paused = False
            print("RESUME")

        blobs = img.find_blobs(
            [BLACK_THRESHOLD],
            roi=DETECTION_ROI,
            pixels_threshold=PIXELS_THRESHOLD,
            area_threshold=AREA_THRESHOLD,
            merge=True,
            margin=2,
        )

        valid_targets = []

        for blob in blobs:
            ok, aspect_ratio, vertical_error, angle_deg = check_vertical_black_rect(blob)

            if ok:
                valid_targets.append((blob, aspect_ratio, vertical_error, angle_deg))
                img.draw_rectangle(blob.rect(), color=255, thickness=2)
                img.draw_cross(blob.cx(), blob.cy(), color=255, size=7)
                img.draw_line(blob.major_axis_line(), color=255, thickness=2)
            else:
                # 用细框标记被剔除的候选，方便调试阈值。
                img.draw_rectangle(blob.rect(), color=100, thickness=1)

        valid_targets.sort(key=lambda item: item[0].pixels(), reverse=True)
        fps = clock.fps()

        # 冷却帧递减。
        if cooldown_frames > 0:
            cooldown_frames -= 1

        # 去重计数状态机。
        if valid_targets:
            lost_frames = 0
            if (not count_latch) and (cooldown_frames == 0):
                target_count += 1
                count_latch = True
                cooldown_frames = COUNT_COOLDOWN_FRAMES
                print("COUNT=%d" % target_count)
        else:
            lost_frames += 1
            if lost_frames >= COUNT_LOST_RESET_FRAMES:
                count_latch = False

        # 指令触发：target_count=3时发送01并暂停识别。
        if (target_count == TRIGGER_COUNT_CMD01) and (not cmd01_sent):
            send_uart_command(uart, CMD_REVERSE_PARK)
            cmd01_sent = True

            # 暂停期间重置去重状态，恢复后按新场景继续识别。
            pause_until_ms = time.ticks_add(time.ticks_ms(), PAUSE_AFTER_CMD01_MS)
            is_paused = True
            count_latch = False
            lost_frames = COUNT_LOST_RESET_FRAMES
            cooldown_frames = 0
            print("PAUSE=%dms" % PAUSE_AFTER_CMD01_MS)

        # 指令触发：target_count=6时发送02。
        if (target_count == TRIGGER_COUNT_CMD02) and (not cmd02_sent):
            send_uart_command(uart, CMD_SIDE_PARK)
            cmd02_sent = True

            # 到6后清零计数，并重置触发标记进入下一轮。
            target_count = 0
            cmd01_sent = False
            cmd02_sent = False
            print("COUNT=0")

        # 仅在需要时打印状态，避免刷屏影响观察计数。
        if (not PRINT_COUNT_ONLY) and ((frame_id % STATUS_PRINT_INTERVAL) == 0):
            if valid_targets:
                best_blob, best_ar, best_err, best_angle = valid_targets[0]
                print(
                    "F=%d DET=1 CNT=%d LAT=%d LOST=%d CD=%d CX=%d CY=%d W=%d H=%d AR=%.2f ANG=%.2f ERR=%.2f FPS=%.2f"
                    % (
                        frame_id,
                        target_count,
                        int(count_latch),
                        lost_frames,
                        cooldown_frames,
                        best_blob.cx(),
                        best_blob.cy(),
                        best_blob.w(),
                        best_blob.h(),
                        best_ar,
                        best_angle,
                        best_err,
                        fps,
                    )
                )
            else:
                print(
                    "F=%d DET=0 CNT=%d LAT=%d LOST=%d CD=%d FPS=%.2f"
                    % (
                        frame_id,
                        target_count,
                        int(count_latch),
                        lost_frames,
                        cooldown_frames,
                        fps,
                    )
                )


if __name__ == "__main__":
    init_camera()
    main_loop()
