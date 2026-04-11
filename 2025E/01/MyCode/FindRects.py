import sensor, image, time, gc, lcd
from machine import UART
from fpioa_manager import fm

# ====================================================
# 1. 硬件引脚映射 & 串口初始化
# ====================================================
# 将 UART2_TX 映射到引脚 8，UART2_RX 映射到引脚 6
fm.register(8, fm.fpioa.UART2_TX, force=True)
fm.register(6, fm.fpioa.UART2_RX, force=True)
# 初始化串口，波特率 9600（需与 STM32 保持一致）
uart = UART(UART.UART2, 9600, 8, 0, 0, timeout=1000, read_buf_len=4096)

# ====================================================
# 2. 屏幕与摄像头初始化
# ====================================================
lcd.init()
lcd.rotation(0)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)

# 先开最大视野
sensor.set_framesize(sensor.QVGA) # 320x240

# 🎯【核心修复】：强制从坐标 (80, 60) 开始，往右往下切一块 160x120 的画面！
# 彻底解决固件乱切左上角导致画面偏左的问题！
sensor.set_windowing((80, 60, 160, 120))

sensor.set_vflip(True)
sensor.set_hmirror(True)

sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.skip_frames(time = 2000)

clock = time.clock()

# 图像的绝对中心点维持不变
SCREEN_CENTER_X = 80
SCREEN_CENTER_Y = 60

while True:
    clock.tick()
    gc.collect() # 内存回收，防止跑久了内存溢出

    img = sensor.snapshot()
    if not img:
        continue

    target_cx = None
    target_cy = None

    # ====================================================
    # 3. 识别靶纸并计算中心
    # ====================================================
    # 这里的 25000 是您在 160x120 分辨率下测试出的完美阈值
    rects = img.find_rects(threshold=25000)

    if rects:
        # 找出面积最大的矩形（过滤掉背景小噪点）
        max_rect = max(rects, key=lambda r: r.w() * r.h())
        if max_rect.w() > 10 and max_rect.h() > 10:
            corners = max_rect.corners()

            # 四点求平均解算透视中心
            target_cx = sum([p[0] for p in corners]) // 4
            target_cy = sum([p[1] for p in corners]) // 4

            # 画出靶纸的绿色外框
            img.draw_rectangle(max_rect.rect(), color=(0, 255, 0), thickness=2)
            # 标出四个角点
            for pt in corners:
                img.draw_circle(pt[0], pt[1], 2, color=(0, 0, 255), fill=True)
            # 在靶纸中心画一个黄色的小十字
            img.draw_cross(target_cx, target_cy, color=(255, 255, 0), size=5)

    # ====================================================
    # 4. 计算偏差、打印并发送给 STM32
    # ====================================================
    final_err_x = 0
    final_err_y = 0

    if target_cx is not None:
        final_err_x = target_cx - SCREEN_CENTER_X
        final_err_y = target_cy - SCREEN_CENTER_Y
        print("锁定靶纸！ 发送误差 -> ErrX: %d, ErrY: %d" % (final_err_x, final_err_y))
    else:
        final_err_x = 0
        final_err_y = 0
        print("未检测到靶纸，发送误差 -> ErrX: 0, ErrY: 0")

    # 数据打包发送 (处理负数，截取低 16 位)
    err_x_int = int(final_err_x) & 0xFFFF
    err_y_int = int(final_err_y) & 0xFFFF

    # 数据帧格式：帧头(0x55 0xAA) + ErrX(高8位 低8位) + ErrY(高8位 低8位) + 帧尾(0xAF)
    data = bytes([
        0x55, 0xAA,
        (err_x_int >> 8) & 0xFF, err_x_int & 0xFF,
        (err_y_int >> 8) & 0xFF, err_y_int & 0xFF,
        0xAF
    ])
    uart.write(data)

    # ====================================================
    # 5. 屏幕 UI 显示
    # ====================================================
    # 在屏幕正中心画一个红色大十字（代表云台机械准心）
    img.draw_cross(SCREEN_CENTER_X, SCREEN_CENTER_Y, color=(255, 0, 0), size=6)

    # 显示当前的误差数值
    info_str = "ErrX:%d  ErrY:%d" % (final_err_x, final_err_y)
    img.draw_string(2, 2, info_str, color=(255, 255, 255), scale=1)

    # 【核心优化 3：画面居中显示】
    # 告诉 LCD 把这块 160x120 的图像，偏移放到 320x240 屏幕的物理正中心！
    lcd.display(img, oft=(80, 60))
