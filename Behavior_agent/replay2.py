import sys
sys.path.append('/home/test/carla/CARLA_0.9.14/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
from config import *
import Acero
from Acero import *
from execute import *
from attack_logging import *
sys.path.append('/home/test/carla/CARLA_0.9.14/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error
import json
import re
import subprocess
import time
import os
import threading
from my_drive_quality import *



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
    subprocess.Popen(['cd ~/carla/CARLA_0.9.14/ && ./CarlaUE4.sh -preferNvidia -rpc-carla-port=2000'], shell=True)

def load_log_data(file_path):
    with open(file_path, 'r') as file:
        log_data = json.load(file)
    return log_data

# 12-12-33.json , 12-12-49.json , 12-14-08.json , 12-14-48.json
# 日志文件路径
# log_file_path = '/home/test/文档/CarlaData001/A001/log/success/25-08-05.json'

# log_file_path = '/home/test/文档/CarlaData001/C001/log/failure/13-05-36.json'
# log_file_path = '/home/test/文档/CarlaData001/C001/log/failure/13-13-26.json'
log_file_path = '/home/test/文档/CarlaData001/C001/log/failure/13-21-57.json'

# 从文件中加载日志数据
log_data = load_log_data(log_file_path)


def main():
    
    start_carla()
    time.sleep(10)  # 等待5秒    
    #连接本地主机的CARLA服务器，端口2000
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0) # 设置超时时间10s

    town="Town03"
    #加载名为 town 的世界。
    client.load_world(town)
    #获取当前加载的世界。
    world = client.get_world()
    #获取观察者
    spectator=world.get_spectator()
    #获取地图
    map=world.get_map()

    # 设置天气
    weather_params = carla.WeatherParameters(
        cloudiness=log_data['mission_setup']['weather']['cloudiness'],
        precipitation=log_data['mission_setup']['weather']['precipitation'],
        precipitation_deposits=log_data['mission_setup']['weather']['precipitation_deposits'],
        sun_altitude_angle=log_data['mission_setup']['weather']['sun_altitude_angle']
    )
    world.set_weather(weather_params)   

    #获取世界中的所有的交通灯
    traffic_lights = world.get_actors().filter('traffic.traffic_light')

    #把世界中所有的交通灯冻结且关闭
    for tl in traffic_lights:
        tl.freeze(True)
        tl.set_state(carla.TrafficLightState.Off)

    # 获取蓝图库
    blueprint_library = world.get_blueprint_library()

    # 设置受害车辆
    victim_bp = blueprint_library.find(log_data['victim_car_details']['model'])
    victim_transform = parse_transform(log_data['victim_car_details']['starting_position'])

    attacker_bp = blueprint_library.find(log_data['attacker_car_details']['model'])
    attacker_transform = parse_transform(log_data['attacker_car_details']['starting_position'])

    npc_bp = blueprint_library.find(log_data['mission_setup']['traffic']['model'][0])
    npc_transform = parse_transform(log_data['mission_setup']['traffic']['traffic_vehicle_starting_positions'][0])
    
    #生成攻击车 受害车 代理 npc
    victim,attacker,agent,npc=scene_init(world,weather_params,attacker_bp,attacker_transform,victim_bp,victim_transform,npc_bp,npc_transform)

    # time.sleep(2)

    history_commands = log_data['attack_commands']


    # 创建1个线程
    cont_throttle = []
    cont_brake = []
    cont_steer = []
    steer_angle_list = []
    speed = []
    speed_lim = []
    yaw_list = []
    yaw_rate_list = []
    lat_speed_list = []
    lon_speed_list = []
    min_dist_list = []
    thread1 = threading.Thread(target=get_data, args=(victim,0,attacker,npc,10,cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist_list))
    # 启动线程
    thread1.start()

    exec_history_command(history_commands,attacker,victim,agent, spectator,world,npc)
    # attacker.apply_control(carla_command(history_commands[len(history_commands)-1]))
    exec_command(attacker,agent,victim, spectator,(history_commands[len(history_commands)-1]),world,npc)

    # time.sleep(20)  # 等待0.3分钟
    
    thread1.join()
    min_dist = min_dist_list[0]
    process_data(cont_throttle,cont_brake,cont_steer,steer_angle_list,speed,speed_lim,yaw_list,yaw_rate_list,lat_speed_list,lon_speed_list,min_dist)

    if is_process_running("CarlaUE4"):
        print("关闭Carla")
        os.system("pkill -f CarlaUE4")  # 关闭Carla




def parse_transform(transform_str):
    # 使用正则表达式提取位置和旋转的数值
    location_pattern = r"Location\(x=(.*?), y=(.*?), z=(.*?)\)"
    rotation_pattern = r"Rotation\(pitch=(.*?), yaw=(.*?), roll=(.*?)\)"
    
    location_match = re.search(location_pattern, transform_str)
    rotation_match = re.search(rotation_pattern, transform_str)
    
    # 如果匹配成功，则创建并返回Transform对象
    if location_match and rotation_match:
        location = carla.Location(
            x=float(location_match.group(1)),
            y=float(location_match.group(2)),
            z=float(location_match.group(3))
        )
        rotation = carla.Rotation(
            pitch=float(rotation_match.group(1)),
            yaw=float(rotation_match.group(2)),
            roll=float(rotation_match.group(3))
        )
        return carla.Transform(location, rotation)
    
    # 如果匹配失败，则返回None
    return None



if __name__ == '__main__':
    
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)