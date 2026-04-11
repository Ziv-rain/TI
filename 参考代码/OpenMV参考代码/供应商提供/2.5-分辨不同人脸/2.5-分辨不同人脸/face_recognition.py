# 使用LBP分辨不同人脸
# 运行此代码前请先运行采集人脸的代码来采集人脸，如果已采集完成，可以运行此代码

import sensor, time, image, pyb

NUM_SUBJECTS = 2                             # 图像库中不同人数
NUM_SUBJECTS_IMGS = 20                       # 每人有20张样本图片
name_list = [None, '迪丽热巴', '鞠婧炜']      # 对应人的名字

# 初始化函数
def init_setup():
    global sensor,face_cascade               # 设置为全局变量
    sensor.reset()                           # 初始化感光元件
    sensor.set_pixformat(sensor.GRAYSCALE)   # 将图像格式设置为灰度
    sensor.set_framesize(sensor.B128X128)    # 将图像大小设置为128x128
    face_cascade = image.HaarCascade("frontalface", stages=25)
    sensor.set_windowing((92,112))           # 将窗口大小设置为92x112
    sensor.skip_frames(10)
    sensor.skip_frames(time=1000)            # 等待1s，使以上设置生效

def min(pmin, a, s):
    global num
    if a < pmin:
        pmin = a
        num = s
    return pmin

# 主函数
def main():
    global num
    # 拍摄当前人脸
    img = sensor.snapshot()
    # d0为当前人脸的lbp特征
    d0 = img.find_lbp((0, 0, img.width(), img.height()))
    objects = img.find_features(face_cascade, threshold=1, scale=1.25)
    if objects:                    # 检测到人脸时
        img = None
        pmin = 999999
        num = 0
        for s in range(1, NUM_SUBJECTS+1):
            dist = 0
            for i in range(1, NUM_SUBJECTS_IMGS+1):
                img = image.Image("ZLTech/s%d/%d.pgm"%(s, i))
                d1 = img.find_lbp((0, 0, img.width(), img.height()))
                # d1为第s文件夹中的第i张图片的lbp特征
                dist += image.match_descriptor(d0, d1)  # 计算d0 d1即样本图像与被检测人脸的特征差异度。
            print("Average dist for subject %d: %d"%(s, dist/NUM_SUBJECTS_IMGS))  # 打印与每个人的特征差异度
            pmin = min(pmin, dist/NUM_SUBJECTS_IMGS, s) # 特征差异度越小，被检测人脸与此样本更相似更匹配。

        print(name_list[num]) # num为当前最匹配的人的编号,然后从名字列表中取出对应人的名字。

# 程序入口
if __name__ == '__main__':
    init_setup()      # 执行初始化函数
    try:              # 异常处理
        while 1:
            main()    # 执行主函数
    except:
        pass
