'''
实验名称:矩形检测
实验平台:01Studio CanMV K230
教程:wiki.01studio.cc
说明:推荐使用320x240以下分辨率，分辨率过大会导致帧率下降。
'''

import time
import gc

from media.sensor import *  #导入sensor模块，使用摄像头相关接口
from media.display import *  #导入display模块，使用display相关接口
from media.media import *  #导入media模块，使用meida相关接口

#导入串口模块
from machine import UART
from machine import FPIOA

fpioa = FPIOA()  # 初始化一个 FPIOA 硬件控制器

# UART1代码
# TX1(GPIO3), RX1(GPIO4)
fpioa.set_function(3, FPIOA.UART1_TXD)
fpioa.set_function(4, FPIOA.UART1_RXD)

uart = UART(UART.UART1, 115200)  #设置串口号1和波特率115200

# 屏幕中心点
# 默认先按方案A全画幅中心，若窗口裁剪成功再切换为K210中心点
SCREEN_CENTER_X = 160
SCREEN_CENTER_Y = 120

# 周期性内存回收计数器
frame_count = 0

# 矩形筛选参数
MIN_RECT_SIDE = 50
MAX_RECT_AREA_RATIO = 0.45

# 检测状态滤波参数
MIN_DETECT_FRAMES = 2
MIN_LOST_FRAMES = 5
MAX_REUSE_FRAMES = 3

# 运行时状态
detect_counter = 0
lost_counter = 0
tracking_locked = False
last_target_cx = None
last_target_cy = None
reuse_counter = 0

# 日志节流参数（减少串口输出对帧率的影响）
LOG_INTERVAL_FRAMES = 20
last_runtime_log_state = "INIT"

# 内存阈值回收参数（优先按阈值触发，缺少接口时退化为低频回收）
GC_CHECK_INTERVAL_FRAMES = 10
GC_FREE_MEM_THRESHOLD = 180 * 1024
GC_FALLBACK_INTERVAL_FRAMES = 150
last_gc_frame = 0


def send_error_k210(uart, err_x, err_y):
    """
    通过UART发送K210兼容误差帧。

    帧格式：55 AA + ErrX(高8位 低8位) + ErrY(高8位 低8位) + AF
    其中误差按16位补码发送，便于与K210原下位机协议保持一致。

    参数:
        uart: 串口对象
        err_x: X方向误差
        err_y: Y方向误差

    返回值:
        无
    """
    err_x_int = int(err_x) & 0xFFFF
    err_y_int = int(err_y) & 0xFFFF

    data = bytes([
        0x55,
        0xAA,
        (err_x_int >> 8) & 0xFF,
        err_x_int & 0xFF,
        (err_y_int >> 8) & 0xFF,
        err_y_int & 0xFF,
        0xAF,
    ])
    uart.write(data)


def calculate_perspective_center(corners):
    """
    通过矩形两条对角线交点计算透视中心点。

    参数:
        corners: 矩形四个角点，格式为[(x1, y1), (x2, y2), (x3, y3), (x4, y4)]

    返回值:
        (center_x, center_y)。当角点数量异常时返回(None, None)。
    """
    if corners is None or len(corners) < 4:
        return None, None

    x1, y1 = corners[0]
    x3, y3 = corners[2]
    x2, y2 = corners[1]
    x4, y4 = corners[3]

    # 两条对角线近乎平行时，退化为四角平均，避免除零。
    denom = (x1 - x3) * (y2 - y4) - (y1 - y3) * (x2 - x4)
    if abs(denom) < 1e-6:
        return sum(p[0] for p in corners) // 4, sum(p[1] for p in corners) // 4

    px = ((x1 * y3 - y1 * x3) * (x2 - x4) - (x1 - x3) * (x2 * y4 - y2 * x4)) / denom
    py = ((x1 * y3 - y1 * x3) * (y2 - y4) - (y1 - y3) * (x2 * y4 - y2 * x4)) / denom

    return int(px), int(py)


sensor = Sensor(width=1280, height=960)  #构建摄像头对象
sensor.reset()  #复位和初始化摄像头

# 方案B（默认）：尽量对齐K210方案，使用320x240再裁剪160x120
sensor.set_framesize(width=320, height=240)

# 方案A（预留对比）：保留全画幅320x240并将中心点设置为(160,120)
# sensor.set_framesize(width=320, height=240)
# SCREEN_CENTER_X = 160
# SCREEN_CENTER_Y = 120

# 优先尝试K210窗口裁剪方案；若固件不支持则自动回退到方案A
if hasattr(sensor, "set_windowing"):
    try:
        sensor.set_windowing((80, 60, 160, 120))
        SCREEN_CENTER_X = 80
        SCREEN_CENTER_Y = 60
        print("已启用K210窗口裁剪方案：160x120")
    except NotImplementedError:
        print("当前固件不支持set_windowing，自动切换到方案A全画幅320x240")
    except Exception as e:
        print("set_windowing调用失败，自动切换到方案A全画幅320x240:", e)
else:
    print("未找到set_windowing接口，自动切换到方案A全画幅320x240")

sensor.set_pixformat(Sensor.RGB565)  #设置输出图像格式，默认通道0

# 图像方向按K210方案设置：上下翻转+左右镜像
if hasattr(sensor, "set_vflip"):
    sensor.set_vflip(False)
if hasattr(sensor, "set_hmirror"):
    sensor.set_hmirror(False)

# 预留曝光与白平衡策略代码：如需固定参数可取消注释后调参
# if hasattr(sensor, "set_auto_gain"):
#     sensor.set_auto_gain(False)
# if hasattr(sensor, "set_auto_whitebal"):
#     sensor.set_auto_whitebal(False)
# if hasattr(sensor, "set_auto_exposure"):
#     sensor.set_auto_exposure(False)

Display.init(Display.ST7701, to_ide=False)  #仅使用3.5寸mipi屏显示图像

MediaManager.init()  #初始化media资源管理器

sensor.run()  #启动sensor

clock = time.clock()

try:
    while True:
        clock.tick()

        # 按空闲内存阈值触发垃圾回收，避免固定周期导致卡顿。
        frame_count += 1
        if frame_count % GC_CHECK_INTERVAL_FRAMES == 0:
            need_gc = False
            if hasattr(gc, "mem_free"):
                try:
                    free_mem = gc.mem_free()
                    if free_mem < GC_FREE_MEM_THRESHOLD:
                        need_gc = True
                except Exception:
                    # mem_free接口异常时回退到低频回收。
                    if frame_count % GC_FALLBACK_INTERVAL_FRAMES == 0:
                        need_gc = True
            elif frame_count % GC_FALLBACK_INTERVAL_FRAMES == 0:
                need_gc = True

            if need_gc and (frame_count - last_gc_frame >= GC_CHECK_INTERVAL_FRAMES):
                gc.collect()
                last_gc_frame = frame_count

        # 显式处理拍照异常与空帧，确保下位机始终收到有效协议帧
        try:
            img = sensor.snapshot()
        except Exception as e:
            if frame_count % LOG_INTERVAL_FRAMES == 0:
                print("拍照异常，发送误差 -> ErrX: 0, ErrY: 0", e)
            send_error_k210(uart, 0, 0)
            continue

        if img is None:
            if frame_count % LOG_INTERVAL_FRAMES == 0:
                print("收到空帧，发送误差 -> ErrX: 0, ErrY: 0")
            send_error_k210(uart, 0, 0)
            continue

        target_cx = None
        target_cy = None

        # 检测阈值按K210方案先设为25000
        rects = img.find_rects(threshold=25000)
        if rects:
            img_area = img.width() * img.height()
            max_rect_area = int(img_area * MAX_RECT_AREA_RATIO)

            # 过滤过小与过大矩形，避免噪声和整幅误检
            valid_rects = []
            for r in rects:
                rect_area = r.w() * r.h()
                if r.w() >= MIN_RECT_SIDE and r.h() >= MIN_RECT_SIDE and rect_area <= max_rect_area:
                    valid_rects.append(r)

            if valid_rects:
                max_rect = max(valid_rects, key=lambda r: r.w() * r.h())
                corners = max_rect.corners()
                target_cx, target_cy = calculate_perspective_center(corners)

                # 可视化检测结果
                img.draw_rectangle(max_rect.rect(), color=(0, 255, 0), thickness=2)
                if target_cx is not None:
                    img.draw_cross(target_cx, target_cy, color=(255, 255, 0), size=5)

        current_detected = (target_cx is not None) and (target_cy is not None)
        used_fallback = False

        # 上一帧回退：短时丢失时沿用最近一次有效中心，降低瞬时跳变。
        if current_detected:
            last_target_cx = target_cx
            last_target_cy = target_cy
            reuse_counter = 0
        elif last_target_cx is not None and reuse_counter < MAX_REUSE_FRAMES:
            target_cx = last_target_cx
            target_cy = last_target_cy
            used_fallback = True
            reuse_counter += 1

        # 连续检测/丢失滤波：避免单帧误检导致状态抖动。
        if current_detected:
            lost_counter = 0
            if not tracking_locked:
                detect_counter += 1
                if detect_counter >= MIN_DETECT_FRAMES:
                    tracking_locked = True
                    detect_counter = 0
            else:
                detect_counter = 0
        else:
            detect_counter = 0
            if tracking_locked:
                lost_counter += 1
                if lost_counter >= MIN_LOST_FRAMES:
                    tracking_locked = False
                    lost_counter = 0
                    reuse_counter = 0
                    last_target_cx = None
                    last_target_cy = None
            else:
                lost_counter = 0

        final_err_x = 0
        final_err_y = 0

        runtime_state = "LOST"
        runtime_log_msg = ""

        if tracking_locked and target_cx is not None:
            final_err_x = target_cx - SCREEN_CENTER_X
            final_err_y = target_cy - SCREEN_CENTER_Y
            if used_fallback:
                runtime_state = "LOCK_FALLBACK"
                runtime_log_msg = "目标短时丢失，沿用上一帧 -> ErrX: %d, ErrY: %d" % (final_err_x, final_err_y)
            else:
                runtime_state = "LOCK"
                runtime_log_msg = "锁定靶纸！发送误差 -> ErrX: %d, ErrY: %d" % (final_err_x, final_err_y)
        elif current_detected:
            runtime_state = "CANDIDATE"
            runtime_log_msg = "检测到候选目标，稳定中(%d/%d)，发送误差 -> ErrX: 0, ErrY: 0" % (detect_counter, MIN_DETECT_FRAMES)
        else:
            runtime_state = "LOST"
            runtime_log_msg = "未检测到靶纸，发送误差 -> ErrX: 0, ErrY: 0"

        if runtime_state != last_runtime_log_state or (frame_count % LOG_INTERVAL_FRAMES == 0):
            print(runtime_log_msg)
            last_runtime_log_state = runtime_state

        # 串口发送K210兼容误差帧
        send_error_k210(uart, final_err_x, final_err_y)

        # 显示机械准心与状态信息（大字号双行）
        img.draw_cross(SCREEN_CENTER_X, SCREEN_CENTER_Y, color=(255, 0, 0), size=6)
        fps_now = clock.fps()
        status_str = "LOCK" if tracking_locked else "SEARCH"
        line_1 = "FPS %.1f %s" % (fps_now, status_str)
        line_2 = "EX %d  EY %d" % (final_err_x, final_err_y)

        # 顶部黑底条，避免白字叠在复杂背景上看不清。
        if hasattr(img, "draw_rectangle"):
            overlay_h = 44 if img.height() >= 120 else 28
            img.draw_rectangle(0, 0, img.width(), overlay_h, color=(0, 0, 0), fill=True)

        if hasattr(img, "draw_string_advanced"):
            img.draw_string_advanced(2, 2, 20, line_1, color=(255, 255, 255))
            img.draw_string_advanced(2, 22, 20, line_2, color=(255, 255, 255))
        elif hasattr(img, "draw_string"):
            img.draw_string(2, 2, line_1, color=(255, 255, 255), scale=2)
            img.draw_string(2, 20, line_2, color=(255, 255, 255), scale=2)

        # 保持当前K230显示链路，按图像尺寸居中显示
        show_w = img.width() if hasattr(img, "width") else sensor.width()
        show_h = img.height() if hasattr(img, "height") else sensor.height()
        Display.show_image(
            img,
            x=round((800 - show_w) / 2),
            y=round((480 - show_h) / 2),
        )
except KeyboardInterrupt:
    print("用户中断程序，准备释放资源")
finally:
    # 在K230上按顺序释放资源，避免下次启动资源占用
    try:
        sensor.stop()
    except Exception as e:
        print("sensor.stop()释放异常:", e)

    try:
        Display.deinit()
    except Exception as e:
        print("Display.deinit()释放异常:", e)

    try:
        MediaManager.deinit()
    except Exception as e:
        print("MediaManager.deinit()释放异常:", e)

    if hasattr(uart, "deinit"):
        try:
            uart.deinit()
        except Exception as e:
            print("uart.deinit()释放异常:", e)

    print("资源释放完成")
