import subprocess
import time
import os

# 定义一个全局变量来存储运行脚本的子进程对象
script_process = None

def is_process_running(process_name):
    """检查指定的进程是否正在运行"""
    try:
        # 使用pgrep命令查找进程名包含process_name的进程
        output = subprocess.check_output(['pgrep', '-f', process_name])
        return True if output else False
    except subprocess.CalledProcessError:
        # 如果pgrep没有找到匹配的进程，会抛出异常
        return False

def start_carla():
    """启动Carla"""
    print("正在启动Carla...")
    subprocess.Popen(['cd ~/carla/CARLA_0.9.13 && ./CarlaUE4.sh -preferNvidia -rpc-carla-port=2000'], shell=True)

def run_script():
    """运行指定的Python脚本"""
    print("运行脚本...")
    global script_process
    script_process = subprocess.Popen(['python3', '/home/test/test050/main.py'])

def main():
    while True:
        start_carla()
        time.sleep(10)  # 等待10秒

        if not is_process_running("CarlaUE4"):
            print("Carla未成功启动，正在重试...")
            continue  # 如果Carla没有启动，重新开始循环
        
        
        run_script()

        start_time = time.time()
        while True:
            time.sleep(10)  # 每10秒检测一次脚本是否运行完毕

            if script_process.poll() is not None:  # 检查脚本进程是否已结束
                print("脚本已运行完毕，重新开始循环...")
                break  # 脚本已运行完毕，跳出内循环，重新开始外循环

            elapsed_time = time.time() - start_time
            if elapsed_time > 240:  # 如果超过240秒仍未完成，重新开始循环
                print("脚本超时，重新开始循环...")
                if script_process is not None:
                    script_process.terminate()  # 终止运行脚本的子进程
                break
            
        if is_process_running("CarlaUE4"):
            print("关闭Carla并重新开始循环...")
            os.system("pkill -f CarlaUE4")  # 关闭Carla
            if script_process is not None:
                script_process.terminate()  # 终止运行脚本的子进程
        else:
            print("Carla已关闭，重新开始循环...")

if __name__ == "__main__":
    main()
