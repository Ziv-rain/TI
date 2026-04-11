# 综合例程
# 包含颜色识别、颜色跟随、人脸识别、人脸跟随、分辨人脸、二维码识别、数字识别、巡线小车、追小球的小车
# 注意颜色相关的需要根据实际情况调节阈值范围，分辨人脸需提前收集好人脸图片
import sensor, image, time, pyb
from pyb import LED
from AI_Functions import (
    multi_color_detection, face_detection, color_tracking, face_tracking,
    face_recognition, qrcode_detection, mutil_template_num_matching,
    car_follow_color, car_follow_line
)
from ZL_SDK import (zl_uart3, zl_led, zl_car_run, zl_pan_tilt, pid)

# 串口接收数据后对应执行的命令值
uart_recv_data_command = None

# 1.对应每个功能的一个标志位，标志位用来初始化一次感光元件 2.串口接收到的对应数据 3.数据对应指令
flag_dict = {
    'multi_color_detection': {'flag': True, 'uart_recv_data': b'$YSSB!', 'command': 'YSSB'},
    'face_detection': {'flag': True, 'uart_recv_data': b'$RLSB!', 'command': 'RLSB'},
    'color_tracking': {'flag': True, 'uart_recv_data': b'$YSGS!', 'command': 'YSGS'},
    'face_tracking': {'flag': True, 'uart_recv_data': b'$RLGS!', 'command': 'RLGS'},
    'face_recognition': {'flag': True, 'uart_recv_data': b'$FBRL!', 'command': 'FBRL'},
    'qrcode_detection': {'flag': True, 'uart_recv_data': b'$EWMSB!', 'command': 'EWMSB'},
    'mutil_template_num_matching': {'flag': True, 'uart_recv_data': b'$SZSB!', 'command': 'SZSB'},
    'car_follow_color': {'flag': True, 'uart_recv_data': b'$ZXQ!', 'command': 'ZXQ'},
    'car_follow_line': {'flag': True, 'uart_recv_data': b'$XJMS!', 'command': 'XJMS'},
}
# 串口接收到对应指令控制小车运动及云台运动
motor_pan_tilt_command_dict = {
    '前进': b'$QJ!',
    '后退': b'$HT!',
    '左转': b'$ZZ!',
    '右转': b'$YZ!',
    '停止': b'$TZ!',
    '复位': b'$RESET!',
}

# 标志位处理函数，标志位用来初始化一次感光元件，并让其他功能对应的flag变为真
def flag_func(flag):
    for i in flag_dict:
        if i == flag:
            flag_dict[i]['flag'] = False
        else:
            flag_dict[i]['flag'] = True
    print(flag_dict)

# 串口接收数据的处理
def uart_recv_data_handle():
    global uart_recv_data_command
    uart_recv_data = zl_uart3.main()
    #print(uart_recv_data, type(uart_recv_data))
    if uart_recv_data:
        if uart_recv_data == flag_dict['multi_color_detection']['uart_recv_data']:        # 颜色识别
            uart_recv_data_command = flag_dict['multi_color_detection']['command']
        elif uart_recv_data == flag_dict['face_detection']['uart_recv_data']:             # 人脸识别
            uart_recv_data_command = flag_dict['face_detection']['command']
        elif uart_recv_data == flag_dict['color_tracking']['uart_recv_data']:             # 颜色跟随
            uart_recv_data_command = flag_dict['color_tracking']['command']
        elif uart_recv_data == flag_dict['face_tracking']['uart_recv_data']:              # 人脸跟随
            uart_recv_data_command = flag_dict['face_tracking']['command']
        elif uart_recv_data == flag_dict['face_recognition']['uart_recv_data']:           # 分辨人脸
            uart_recv_data_command = flag_dict['face_recognition']['command']
        elif uart_recv_data == flag_dict['qrcode_detection']['uart_recv_data']:           # 二维码识别
            uart_recv_data_command = flag_dict['qrcode_detection']['command']
        elif uart_recv_data == flag_dict['mutil_template_num_matching']['uart_recv_data']: # 数字识别
            uart_recv_data_command = flag_dict['mutil_template_num_matching']['command']
        elif uart_recv_data == flag_dict['car_follow_color']['uart_recv_data']:           # 追小球
            uart_recv_data_command = flag_dict['car_follow_color']['command']
        elif uart_recv_data == flag_dict['car_follow_line']['uart_recv_data']:            # 循迹模式
            uart_recv_data_command = flag_dict['car_follow_line']['command']
        elif uart_recv_data == motor_pan_tilt_command_dict['前进']:                       # 前进
            zl_car_run.car_run(zl_car_run.forward_speed, zl_car_run.forward_speed)
            uart_recv_data_command = 'QJ'
        elif uart_recv_data == motor_pan_tilt_command_dict['后退']:                       # 后退
            zl_car_run.car_run(zl_car_run.backward_speed, zl_car_run.backward_speed)
            uart_recv_data_command = 'HT'
        elif uart_recv_data == motor_pan_tilt_command_dict['左转']:                       # 左转
            zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.forward_speed)
            uart_recv_data_command = 'ZZ'
        elif uart_recv_data == motor_pan_tilt_command_dict['右转']:                       # 右转
            zl_car_run.car_run(zl_car_run.forward_speed, zl_car_run.stop_speed)
            uart_recv_data_command = 'YZ'
        elif uart_recv_data == motor_pan_tilt_command_dict['停止']:                       # 停止
            zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.stop_speed)
            uart_recv_data_command = 'TZ'
            LED(1).off()
            LED(2).off()
            LED(3).off()
        elif uart_recv_data == motor_pan_tilt_command_dict['复位']:                       # 复位
            zl_pan_tilt.middle()
            uart_recv_data_command = 'FW'
        #print(uart_recv_data_command)


# 功能执行函数
def function_run():
    if uart_recv_data_command == flag_dict['multi_color_detection']['command']:  # 颜色识别功能
        if flag_dict['multi_color_detection']['flag']:                           # 只初始化一次
            multi_color_detection.init_setup()                                   # 颜色识别初始化
            flag_func('multi_color_detection')
        multi_color_detection.main()                                             # 执行颜色识别主函数

    elif uart_recv_data_command == flag_dict['face_detection']['command']:       # 人脸识别功能
        if flag_dict['face_detection']['flag']:                                  # 只初始化一次
            face_detection.init_setup()                                          # 人脸识别初始化
            flag_func('face_detection')
        face_detection.main()                                                    # 执行人脸识别主函数

    elif uart_recv_data_command == flag_dict['color_tracking']['command']:       # 颜色跟随功能
        if flag_dict['color_tracking']['flag']:                                  # 只初始化一次
            color_tracking.init_setup()                                          # 颜色跟随初始化
            flag_func('color_tracking')
        color_tracking.main()                                                    # 执行颜色跟随主函数

    elif uart_recv_data_command == flag_dict['face_tracking']['command']:        # 人脸跟随功能
        if flag_dict['face_tracking']['flag']:                                   # 只初始化一次
            face_tracking.init_setup()                                           # 人脸跟随初始化
            flag_func('face_tracking')
        face_tracking.main()                                                     # 执行人脸跟随主函数

    elif uart_recv_data_command == flag_dict['face_recognition']['command']:     # 分辨人脸功能
        if flag_dict['face_recognition']['flag']:                                # 只初始化一次
            face_recognition.init_setup()                                        # 分辨人脸初始化
            flag_func('face_recognition')
        face_recognition.main()                                                  # 执行分辨人脸主函数

    elif uart_recv_data_command == flag_dict['qrcode_detection']['command']:     # 二维码识别功能
        if flag_dict['qrcode_detection']['flag']:                                # 只初始化一次
            qrcode_detection.init_setup()                                        # 二维码识别初始化
            flag_func('qrcode_detection')
        qrcode_detection.main()                                                  # 执行二维码主函数

    elif uart_recv_data_command == flag_dict['mutil_template_num_matching']['command']:  # 数字识别功能
        if flag_dict['mutil_template_num_matching']['flag']:                     # 只初始化一次
            mutil_template_num_matching.init_setup()                             # 数字识别初始化
            flag_func('mutil_template_num_matching')
        mutil_template_num_matching.main()                                       # 执行数字识别主函数

    elif uart_recv_data_command == flag_dict['car_follow_color']['command']:     # 追小球功能
        if flag_dict['car_follow_color']['flag']:                                # 只初始化一次
            car_follow_color.init_setup()                                        # 追小球功能初始化
            flag_func('car_follow_color')
        car_follow_color.main()                                                  # 执行追小球主函数

    elif uart_recv_data_command == flag_dict['car_follow_line']['command']:      # 循迹功能
        if flag_dict['car_follow_line']['flag']:                                 # 只初始化一次
            car_follow_line.init_setup()                                         # 循迹模式初始化
            flag_func('car_follow_line')
        car_follow_line.main()                                                   # 执行循迹主函数

# 主函数
def main():
    uart_recv_data_handle()  # 串口接收数据并处理
    function_run()           # 根据接收到的数据执行不同的功能


# 程序入口
if __name__ == '__main__':
    zl_led.init_setup()      # led灯初始化
    zl_uart3.init_setup()    # 串口初始化
    for i in range(6):       # led灯亮三下，代表初始化完成，可以开始执行各项功能了
        zl_led.main(0.3)     # 每次亮0.3秒
    zl_pan_tilt.middle()     # 云台在程序开始后复位
    try:                     # 异常处理
        while 1:             # 无限循环
            main()           # 执行主函数
    except:
        zl_pan_tilt.middle() # 云台复位
        zl_car_run.car_run(zl_car_run.stop_speed, zl_car_run.stop_speed)  # 小车停止
