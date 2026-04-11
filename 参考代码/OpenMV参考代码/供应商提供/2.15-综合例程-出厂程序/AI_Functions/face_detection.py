"""
人脸识别例程
这个例子展示了OpenMV Cam的内置人脸检测功能。
人脸检测通过在图像上使用Haar Cascade特征检测器来工作。 haar级联是一系列简单的区域对比检查。
对于内置的前表面探测器，有25个阶段的检查，每个阶段有数百个检查一块。 Haar Cascades运行速度
很快，因为只有在以前的阶段过去后才会评估后期阶段。 此外，您的OpenMV使用称为整体图像的数据
结构来在恒定时间内快速执行每个区域对比度检查
（特征检测仅为灰度的原因是因为整体图像的空间需求）。
"""
import sensor, image, time

# 初始化函数
def init_setup():
    # 设置为全局变量
    global sensor, face_cascade, clock
    # 重置感光元件
    sensor.reset()
    # 感光元件设置
    sensor.set_contrast(3)
    sensor.set_gainceiling(16)
    # HQVGA和灰度对于人脸识别效果最好，240x160
    sensor.set_framesize(sensor.HQVGA)
    # 注意人脸识别只能用灰度图哦
    sensor.set_pixformat(sensor.GRAYSCALE)
    # 创建时钟对象
    clock = time.clock()

    # 加载Haar算子
    # 默认情况下，这将使用所有阶段，更低的satges更快，但不太准确。
    face_cascade = image.HaarCascade("frontalface", stages=25)
    # image.HaarCascade(path, stages=Auto)加载一个haar模型。haar模型是二进制文件，
    # 这个模型如果是自定义的，则引号内为模型文件的路径；也可以使用内置的haar模型，
    # 比如“frontalface” 人脸模型或者“eye”人眼模型。
    # stages值未传入时使用默认的stages。stages值设置的小一些可以加速匹配，但会降低准确率。
    # print(face_cascade)

# 主函数
def main():
    clock.tick()               # 更新FPS帧率时钟
    img = sensor.snapshot()    # 拍摄一张照片

    objects = img.find_features(face_cascade, threshold=0.75, scale=1.25)
    # image.find_features(cascade, threshold=0.5, scale=1.5),thresholds越大，
    # 匹配速度越快，错误率也会上升。scale可以缩放被匹配特征的大小。
    if objects:                # 检测到人脸时
        for r in objects:
            img.draw_rectangle(r)  # 在找到的目标上画框，标记出来
            print(r)               # 打印人脸的左上角坐标、人脸宽度高度
    else:                      # 未检测到人脸时
        print("FPS %f" % clock.fps())  # 打印帧率

# 程序入口
if __name__ == '__main__':
    init_setup()                   # 初始化函数
    try:                           # 异常处理
        while 1:                   # 无限循环
            main()                 # 执行主函数
    except:
        pass
