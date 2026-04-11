# Tensorflow口罩识别

import sensor, time, ml, uos, gc

net = None
labels = None

# 初始化函数
def mask_init_setup():
    global sensor, net, labels, clock      # 设置为全局变量
    sensor.reset()                         # 初始化感光元件
    sensor.set_pixformat(sensor.RGB565)    # 设置图像格式为彩色
    sensor.set_framesize(sensor.QVGA)      # 设置图像大小为QVGA (320x240)
    sensor.set_windowing((240, 240))       # 设置window窗口大小为240x240
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

    clock = time.clock()                   # 创建时钟对象

# 主函数
def mask_main():
    while 1:
        clock.tick()                # 更新FPS帧率时钟
        img = sensor.snapshot()     # 拍一张照片并返回图像

        # 预测率列表
        predictions_list = list(net.predict([img])[0].flatten().tolist())
        #print('predictions_list = ', predictions_list)
        # 预测率中最匹配的那个概率
        prediction_max = max(predictions_list)
        #print('prediction_max = ', prediction_max)
        # 判断最匹配的概率是否大于0.9
        if prediction_max > 0.9:
            # 最匹配的那个概率在列表中的索引位置
            prediction_max_index = predictions_list.index(prediction_max)
            #print('prediction_max_index = ', prediction_max_index)
            # 从要识别的物体列表中找到最匹配概率索引所对应的物体
            result = labels[prediction_max_index]
            #print('labels = ', labels)
            if result == 'mask':
                # 打印识别到的类别
                print('检测到已戴好口罩')
            elif result == 'face':
                print('检测到未佩戴口罩，请佩戴好口罩')

'''

        # default settings just do one detection... change them to search the image...
        for obj in net.classify(img, min_scale=1.0, scale_mul=0.8, x_overlap=0.5, y_overlap=0.5):
            #print("**********\nPredictions at [x=%d,y=%d,w=%d,h=%d]" % obj.rect())
            img.draw_rectangle(obj.rect())
            # 将分类和对应的相似度以列表套元组形式返回
            predictions_list = list(zip(labels, obj.output()))
            # 打印分类和与图像中检测到的物体的对应的相似度
            #for i in range(len(predictions_list)):
                #print("%s = %f" % (predictions_list[i][0], predictions_list[i][1]))
            if max(obj.output()) > 0.9:   # 当识别到的最大的相似度大于0.9时才认为是识别到了
                # 将识别到的类别赋值给result
                result = labels[obj.output().index(max(obj.output()))]
                if result == 'mask':
                    # 打印识别到的类别
                    print('检测到已戴好口罩')
                elif result == 'face':
                    print('检测到未佩戴口罩，请佩戴好口罩')
'''
        #print(clock.fps(), "fps")  # 打印帧率

# 程序入口
if __name__ == '__main__':
    mask_init_setup()  # 执行初始化函数
    try:
        mask_main()    # 执行主函数
    except:
        pass
