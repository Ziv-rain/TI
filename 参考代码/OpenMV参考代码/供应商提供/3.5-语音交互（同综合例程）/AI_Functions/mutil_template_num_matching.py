# 多模板匹配
#
# 通过多模板匹配进行数字识别

import time, sensor, image
# 从imgae模块引入SEARCH_EX和SEARCH_DS
from image import SEARCH_EX, SEARCH_DS

# 初始化函数
def init_setup():
    global sensor, templates, clock
    # 初始化感光元件
    sensor.reset()

    # 感光元件设置
    sensor.set_contrast(1)
    sensor.set_gainceiling(16)
    # 设置图像分辨率为 QQVGA，即160x120
    sensor.set_framesize(sensor.QQVGA)
    # 设置为灰度图
    sensor.set_pixformat(sensor.GRAYSCALE)

    # 模型图片
    templates = ["/models/template_num/0.pgm", "/models/template_num/1.pgm", "/models/template_num/2.pgm",
                "/models/template_num/3.pgm","/models/template_num/4.pgm", "/models/template_num/5.pgm",
                "/models/template_num/6.pgm", "/models/template_num/7.pgm", "/models/template_num/8.pgm",
                "/models/template_num/9.pgm"]     # 保存多个模板
    # 加载模板图片
    # 创建时钟对象
    clock = time.clock()

# 主函数
def main():
    clock.tick()                # 更新FPS帧率时钟
    img = sensor.snapshot()     # 拍摄一张照片

    for t in templates:
        template = image.Image(t)
        # 对每个模板遍历进行模板匹配
        r = img.find_template(template, 0.70, step=4, search=SEARCH_EX) #, roi=(10, 0, 60, 60))
        # 在find_template(template, threshold, [roi, step, search]),threshold中
        # 0.7是相似度阈值,roi是进行匹配的区域（左上顶点为（10，0），长80宽60的矩形），
        # 注意roi的大小要比模板图片大，比frambuffer小。
        # 把匹配到的图像标记出来
        if r:
            img.draw_rectangle(r)
            print('识别到的数字是 %s' % t.split('/')[-1][0]) # 打印识别到的数字

    # print(clock.fps())

# 程序入口
if __name__ == '__main__':
    init_setup()    # 执行初始化函数
    try:
        while 1:
            main()      # 执行主函数
    except:
        pass
