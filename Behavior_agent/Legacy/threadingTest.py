import threading
import time

# 定义第一个要运行的函数
def function1():
    for i in range(5):
        print("Function 1 is running.")
        # time.sleep(1)

# 定义第二个要运行的函数
def function2():
    for i in range(5):
        print("Function 2 is running.")
        # time.sleep(1)

# 创建两个线程
thread1 = threading.Thread(target=function1)
thread2 = threading.Thread(target=function2)

# 启动线程
thread1.start()
thread2.start()

# 等待线程结束
thread1.join()
thread2.join()

print("Both functions have finished executing.")
