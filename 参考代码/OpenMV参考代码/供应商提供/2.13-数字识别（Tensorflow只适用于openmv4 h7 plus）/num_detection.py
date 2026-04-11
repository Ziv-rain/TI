# Tensorflow数字识别

import sensor, time, ml, uos, gc

net = None
labels = None

# 初始化函数
def num_init_setup():
    global sensor, net, labels, clock      # 设置为全局变量
    sensor.reset()                         # 初始化感光元件
    sensor.set_pixformat(sensor.GRAYSCALE) # 设置图像格式为灰度
    sensor.set_framesize(sensor.QVGA)      # 设置图像大小为 QVGA (320x240)
    sensor.set_windowing((240, 240))       # 设置窗口大小为 240x240
    sensor.skip_frames(10)                 # 跳过一些帧，使以上设置生效

    try:
        # 加载模型文件
        net = ml.Model("trained.tflite", load_to_fb=uos.stat('trained.tflite')[6] > (gc.mem_free() - (64*1024)))
    except Exception as e:
        print(e)
        raise Exception('Failed to load "trained.tflite", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

    try:
        labels = [line.rstrip('\n') for line in open("labels.txt")]
    except Exception as e:
        raise Exception('Failed to load "labels.txt", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')

    clock = time.clock()        # 创建时钟对象

# 主函数
def num_main():
    while 1:
        clock.tick()                # 更新FPS帧率时钟
        img = sensor.snapshot()     # 拍一张照片并返回图像
        # 预测率列表
        predictions_list = list(net.predict([img])[0].flatten().tolist())
        #print('predictions_list = ', predictions_list)
        # 预测率中最匹配的那个概率
        prediction_max = max(predictions_list)
        #print('prediction_max = ', prediction_max)
        # 判断最匹配的概率是否大于0.8
        if prediction_max > 0.8:
            # 最匹配的那个概率在列表中的索引位置
            prediction_max_index = predictions_list.index(prediction_max)
            #print('prediction_max_index = ', prediction_max_index)
            # 从要识别的物体列表中找到最匹配概率索引所对应的物体
            num = labels[prediction_max_index]
            #print('labels = ', labels)
            print('识别到的数字是 %s' % num)


# 程序入口
if __name__ == '__main__':
    num_init_setup()  # 执行初始化函数
    try:
        num_main()    # 执行主函数
    except:
        pass
