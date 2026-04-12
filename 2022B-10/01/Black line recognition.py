import sensor
import time
from pyb import UART


# ====== 图像参数（需现场调参） ======
BLACK_GRAY_THRESHOLD = (0, 90)  # 黑胶带阈值（灰度）
WHITE_BINARY_THRESHOLD = (200, 255)  # binary 后白色目标阈值

PIXELS_THRESHOLD = 80
AREA_THRESHOLD = 80
MIN_BLOB_W = 2
MIN_BLOB_H = 12
MIN_ASPECT_RATIO = 1.2  # 竖线约束：h / w 需要足够大

# 抗断裂预处理参数（针对黑线中间被高光切断）
SMOOTH_MEAN_KSIZE = 1
CLOSE_DILATE_ITER = 2
CLOSE_ERODE_ITER = 1
BLOB_MERGE_MARGIN = 12

ROI_TOP = 20  # 忽略上方远处区域，降低干扰
UNLOCK_MISS_FRAMES = 3  # 丢失若干帧后，允许识别下一条线
MIN_MOVE_RIGHT_PX = 6  # 判定“向右划过”的最小像素位移


# ====== 距离判定参数（基于通过时间差） ======
# 在“一次只能看到一条黑线”的场景中，用相邻黑线的通过时间差估算间距。
VEHICLE_SPEED_CM_S = 12.0 # 小车直行速度(cm/s)，必须现场标定
TARGET_23_CM = 23.0
TARGET_50_CM = 50.0
TOLERANCE = 0.10  # 允许误差 ±10%

# 第三条黑线后发送：
# 第一条作为基准，从第二条开始得到一次间距，所以第三条对应 2 次有效间距。
TRIGGER_INTERVAL_COUNT = 2

# 第三条线识别到后，延时发送指令（毫秒），可直接调整。
SEND_DELAY_MS = 0

# 是否在间距不匹配时清零计数。建议 True，避免非连续匹配误触发。
RESET_ON_MISMATCH = True


# ====== 串口协议 ======
UART_BAUD = 115200
FRAME_HEAD_1 = 0xAA
FRAME_HEAD_2 = 0x55
DATA_LEN = 0x00

CMD_REVERSE_PARK = 0x01  # 倒车入库
CMD_SIDE_PARK = 0x02  # 侧方入库


uart3 = None


def ticks_ms():
    return time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)


def ticks_diff(now_ms, old_ms):
    return time.ticks_diff(now_ms, old_ms) if hasattr(time, "ticks_diff") else (now_ms - old_ms)


def ticks_add(base_ms, delta_ms):
    return time.ticks_add(base_ms, delta_ms) if hasattr(time, "ticks_add") else (base_ms + delta_ms)


def init_sensor():
    # 初始化相机为灰度模式，提升速度与稳定性。
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QQVGA)
    sensor.skip_frames(time=1200)

    # 关闭自动增益和自动白平衡，避免阈值漂移。
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False)


def init_uart(baud=UART_BAUD):
    global uart3
    uart3 = UART(3, baud)
    uart3.init(baud, 8, None, 1)
    print("串口初始化完成: %d 8N1" % baud)


def cm_in_range(value_cm, target_cm):
    low = target_cm * (1.0 - TOLERANCE)
    high = target_cm * (1.0 + TOLERANCE)
    return low <= value_cm <= high


def estimate_distance_cm(delta_ms):
    return VEHICLE_SPEED_CM_S * (delta_ms / 1000.0)


def send_uart_packet(cmd):
    global uart3
    checksum = (FRAME_HEAD_1 + FRAME_HEAD_2 + cmd + DATA_LEN) & 0xFF
    packet = bytearray([FRAME_HEAD_1, FRAME_HEAD_2, cmd, DATA_LEN, checksum])
    uart3.write(packet)
    print("TX:", [hex(x) for x in packet])


def detect_vertical_black_line(img, roi):
    # 先做轻微平滑，减少地砖纹理与高光噪声。
    img.mean(SMOOTH_MEAN_KSIZE)

    # 二值化后做“闭运算”（先膨胀后腐蚀），优先连接断裂的黑线。
    img.binary([BLACK_GRAY_THRESHOLD])
    img.dilate(CLOSE_DILATE_ITER)
    img.erode(CLOSE_ERODE_ITER)

    blobs = img.find_blobs(
        [WHITE_BINARY_THRESHOLD],
        roi=roi,
        pixels_threshold=PIXELS_THRESHOLD,
        area_threshold=AREA_THRESHOLD,
        merge=True,
        margin=BLOB_MERGE_MARGIN,
    )

    best_blob = None
    best_score = 0

    for blob in blobs:
        w = blob.w()
        h = blob.h()
        if w < MIN_BLOB_W or h < MIN_BLOB_H:
            continue

        aspect_ratio = h / float(w)
        if aspect_ratio < MIN_ASPECT_RATIO:
            continue

        score = blob.pixels()
        if score > best_score:
            best_score = score
            best_blob = blob

    return best_blob


def main():
    init_sensor()
    init_uart()

    clock = time.clock()
    w = sensor.width()
    h = sensor.height()
    roi = (0, ROI_TOP, w, h - ROI_TOP)

    # 两个独立计数器：记录有效间距次数。
    cnt_23cm = 0
    cnt_50cm = 0

    # 记录上一条黑线“有效通过事件”的时间。
    last_line_event_ms = None

    # 延时发送队列（第三条线触发后可延时发送）。
    pending_cmd = None
    pending_send_deadline = None

    # line_locked=True 表示当前这条线还在视野中，防止重复计数。
    line_locked = False
    line_counted = False
    line_start_cx = None
    line_max_cx = None

    miss_frames = 0
    debug_tick = 0

    print("系统启动，等待黑线...")

    while True:
        clock.tick()
        now_ms = ticks_ms()

        # 到达计划发送时间则立即发送。
        if pending_cmd is not None and ticks_diff(now_ms, pending_send_deadline) >= 0:
            send_uart_packet(pending_cmd)
            print("延时发送完成: cmd=0x%02X" % pending_cmd)
            pending_cmd = None
            pending_send_deadline = None

        img = sensor.snapshot()
        img.draw_rectangle(roi, color=127)

        blob = detect_vertical_black_line(img, roi)

        if blob:
            img.draw_rectangle(blob.rect(), color=255)
            img.draw_cross(blob.cx(), blob.cy(), color=255)
            miss_frames = 0
            cx = blob.cx()

            if not line_locked:
                # 新黑线刚进入视野。
                line_locked = True
                line_counted = False
                line_start_cx = cx
                line_max_cx = cx

            else:
                # 同一条线在画面内向右划过时，cx 会持续增大。
                if cx > line_max_cx:
                    line_max_cx = cx

                # 达到最小右移阈值后，确认“这一条线出现有效”，只计数一次。
                if (not line_counted) and ((line_max_cx - line_start_cx) >= MIN_MOVE_RIGHT_PX):
                    line_counted = True

                    if last_line_event_ms is None:
                        # 第一条线只作为基准，不参与间距计数。
                        last_line_event_ms = now_ms
                        print("第一条黑线(基准线): cx_start=%d cx_now=%d" % (line_start_cx, cx))
                    else:
                        delta_ms = ticks_diff(now_ms, last_line_event_ms)
                        last_line_event_ms = now_ms
                        distance_cm = estimate_distance_cm(delta_ms)

                        if cm_in_range(distance_cm, TARGET_23_CM):
                            cnt_23cm += 1
                            cnt_50cm = 0
                            print(
                                "间距估算=%.2fcm -> 23cm, cnt_23cm=%d"
                                % (distance_cm, cnt_23cm)
                            )

                            if cnt_23cm >= TRIGGER_INTERVAL_COUNT:
                                if pending_cmd is None:
                                    pending_cmd = CMD_REVERSE_PARK
                                    pending_send_deadline = ticks_add(now_ms, SEND_DELAY_MS)
                                    print(
                                        "检测到第三条23cm线，%dms后发送倒车入库"
                                        % SEND_DELAY_MS
                                    )
                                cnt_23cm = 0

                        elif cm_in_range(distance_cm, TARGET_50_CM):
                            cnt_50cm += 1
                            cnt_23cm = 0
                            print(
                                "间距估算=%.2fcm -> 50cm, cnt_50cm=%d"
                                % (distance_cm, cnt_50cm)
                            )

                            if cnt_50cm >= TRIGGER_INTERVAL_COUNT:
                                if pending_cmd is None:
                                    pending_cmd = CMD_SIDE_PARK
                                    pending_send_deadline = ticks_add(now_ms, SEND_DELAY_MS)
                                    print(
                                        "检测到第三条50cm线，%dms后发送侧方入库"
                                        % SEND_DELAY_MS
                                    )
                                cnt_50cm = 0

                        else:
                            print("间距估算=%.2fcm -> 不匹配" % distance_cm)
                            if RESET_ON_MISMATCH:
                                cnt_23cm = 0
                                cnt_50cm = 0

        else:
            if line_locked:
                miss_frames += 1
                if miss_frames >= UNLOCK_MISS_FRAMES:
                    # 当前线已离开视野，解锁等待下一条线。
                    line_locked = False
                    line_counted = False
                    line_start_cx = None
                    line_max_cx = None
                    miss_frames = 0

        debug_tick += 1
        if debug_tick % 20 == 0:
            print(
                "cnt23=%d cnt50=%d pending=%s fps=%.1f"
                % (cnt_23cm, cnt_50cm, str(pending_cmd), clock.fps())
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Runtime error:", e)
