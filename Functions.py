# -*- coding: utf-8 -*-
"""
Created on Thu May 23 21:47:27 2019

@author: ASUS
"""

import tensorflow as tf
import cv2
import numpy as np
import os
import random
import sys
from sklearn.model_selection import train_test_split

def getPaddingSize(img): #对于不是正方形的图片，上下左右分别需要补充多少行或者多少列
    h,w,_=img.shape
    top,bottom,left,right=(0,0,0,0)
    longest=max(h,w)

    if w<longest:
        tmp=longest-w
        # // 表示整除符号
        left=tmp//2
        right=tmp-left
    elif h<longest:
        tmp=longest-h
        top=tmp//2
        bottom=tmp-top
    else:
        pass
    return top,bottom,left,right

def readData(path,h=size,w=size):
    for filename in os.listdir(path): #os.listdir(path) 返回指定路径下所有文件和文件夹的名字，并存放于一个列表中。
        if filename.endswith('.jpg'):
            filename=path+'/'+filename

            img=cv2.imread(filename)

            top,bottom,left,right=getPaddingSize(img)
            #将图片放大，扩充图片边缘部分
            img=cv2.copyMakeBorder(img,top,bottom,left,right,cv2.BORDER_CONSTANT,value=[0,0,0])
            img=cv2.resize(img,(h,w))

            imgs.append(img)
            #添加标签，根据路径判别类别
            if path==my_faces_path:
                labs.append([0,1])
            else:
                labs.append([1,0])
            # labs.append(path)
            
#随机权值向量
def weightVariable(shape):
    init = tf.random_normal(shape,stddev=0.01)
    return tf.Variable(init)

#随机偏置向量
def baisVariable(shape): #def biasVariable(shape):
    init=tf.random_normal(shape)
    return tf.Variable(init)

#定义卷积函数
def conv2d(x,W):
    return tf.nn.conv2d(x,W,strides=[1,1,1,1],padding='SAME')

#定义最大池化
def maxPool(x):
    return tf.nn.max_pool(x,ksize=[1,2,2,1],strides=[1,2,2,1],padding='SAME')

#定义丢失函数
def dropout(x,keep):
    return tf.nn.dropout(x,keep)

#建立cnn训练模型
def cnnLayer():
    #第一层
    #卷积核大小（3,3） 通道是3 输出通道32
    W1=weightVariable([3,3,3,32])
    b1=baisVariable([32])

    #卷积
    conv1=tf.nn.relu(conv2d(x,W1)+b1)
    #池化
    pool1=maxPool(conv1)
    #减少过拟合，随机让某些权值不更新
    drop1=dropout(pool1,keep_prob_5)

    #第二层
    W2=weightVariable([3,3,32,64])
    b2=baisVariable([64])
    conv2=tf.nn.relu(conv2d(drop1,W2)+b2)
    pool2=maxPool(conv2)
    drop2=dropout(pool2,keep_prob_5)

    #第三层
    W3=weightVariable([3,3,64,64])
    b3=baisVariable([64])
    conv3=tf.nn.relu(conv2d(drop2,W3)+b3)
    pool3=maxPool(conv3)
    drop3=dropout(pool3,keep_prob_5)

    #全连接层
    Wf=weightVariable([64*64,512])
    bf=baisVariable([512])
    #将特征图展开
    drop3_flat=tf.reshape(drop3,[-1,8*8*64]) #每一张图片的尺寸，是什么时候变为8*8*64的？
    dense=tf.nn.relu(tf.matmul(drop3_flat,Wf)+bf)
    dropf=dropout(dense,keep_prob_75)

    #输出层
    Wout=weightVariable([512,2])
    bout=weightVariable([2])

    out=tf.add(tf.matmul(dropf,Wout),bout)
    return out

def cnnTrain():
    out =cnnLayer()
    #损失函数
    cross_entropy=tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=out,labels=y_))
    #优化器
    train_step=tf.train.AdamOptimizer(0.01).minimize(cross_entropy)
    #比较标签是否相等，再求得所有数的平均值
    accuaracy=tf.reduce_mean(tf.cast(tf.equal(tf.argmax(out,1),tf.argmax(y_,1)),tf.float32))

    #将loss与accuary 保存以供tensorboard使用
    tf.summary.scalar('loss',cross_entropy)
    tf.summary.scalar('accuracy',accuaracy)

    #使用merge_all 可以管理我们的summary 但是容易出错
    merged_summary_op=tf.summary.merge_all()

    #数据保存器初始化
    saver=tf.train.Saver()

    with tf.Session(config=tf.ConfigProto(log_device_placement=True)) as sess:
        #初始化所有向量
        sess.run(tf.global_variables_initializer())
        summary_writer=tf.summary.FileWriter('./tmp',graph=tf.get_default_graph())
        index=0
        for n in range(10): #多少个epoch
            #每次取128（batch_size）张图片
            for i in range(num_batch): #一个epoch包含多少个批
                batch_x=train_x[i*batch_size:(i+1)*batch_size] #按照顺序取批，而不是随机取
                batch_y=train_y[i*batch_size:(i+1)*batch_size]

                #开始训练数据，同时训练三个变量，返回三个数据
                _,loss,summary=sess.run([train_step,cross_entropy,merged_summary_op],
                                        feed_dict={x:batch_x,y_:batch_y,keep_prob_5:0.5,keep_prob_75:0.75})

                summary_writer.add_summary(summary,n*num_batch+i)
                #打印损失
                print('次数 %d ,lossing: %.4f' % (n*num_batch+i,loss))

                if (n*num_batch+i)%100==0:
                    #获取测试数据的准确率
                    acc=sess.run(accuaracy,feed_dict={x:test_x,y_:test_y,keep_prob_5:1.0,keep_prob_75:1.0})
                    print('次数 %d , 准确率: %.4f' % (n*num_batch+i,acc))
                    #当准确率连续十次大于0.99时  保存并退出
                    if acc>0.99:
                        index+=1
                    else:
                        index=0
                    if index>10:
                        # model_path=os.path.join(os.getcwd(),'train_faces.model')
                        saver.save(sess,'./tmp/train_faces.model',global_step=n*num_batch+i)
                        sys.exit(0)
        print('accuary less 0.99,exited!')