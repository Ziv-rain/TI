import math
import sensor
import time


# =========================
# 可调参数（先在现场标定这些参数）
# =========================

# 灰度阈值：用于提取黑色目标（值越小越黑）
BLACK_THRESHOLD = (0, 55)

# 候选区域最小像素和面积，过滤小噪声
PIXELS_THRESHOLD = 120
AREA_THRESHOLD = 120

# 几何筛选：竖直矩形应“高明显大于宽”
MIN_WIDTH = 6
MIN_HEIGHT = 16
MIN_ASPECT_RATIO = 1.8
MIN_DENSITY = 0.45
MIN_ELONGATION = 0.45

# 竖直角度容差（度）：误差越小越严格
VERTICAL_TOLERANCE_DEG = 3.0


def init_camera():
    """初始化OpenMV相机参数。"""
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.QQVGA)
    sensor.set_auto_gain(False)
    sensor.skip_frames(time=2000)


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

    while True:
        clock.tick()
        img = sensor.snapshot()
        frame_id += 1

        blobs = img.find_blobs(
            [BLACK_THRESHOLD],
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

        if valid_targets:
            best_blob, best_ar, best_err, best_angle = valid_targets[0]
            print(
                "F=%d DET=1 CAND=%d OK=%d CX=%d CY=%d W=%d H=%d AR=%.2f ANG=%.2f ERR=%.2f FPS=%.2f"
                % (
                    frame_id,
                    len(blobs),
                    len(valid_targets),
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
            print("F=%d DET=0 CAND=%d OK=0 FPS=%.2f" % (frame_id, len(blobs), fps))


if __name__ == "__main__":
    init_camera()
    main_loop()

