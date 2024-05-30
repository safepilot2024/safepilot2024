import carla
import time
from attack_logging import *
import json
import re
import time
import os
from acero_main import *
from send_message import *
import until
from until import *
import datetime
from attack_logging import *
from random_test import *


def load_log_data(file_path):
    with open(file_path, 'r') as file:
        log_data = json.load(file)
    return log_data

log_file_path = '/home/test/文档/CarlaData002/R001/log/success/05-23-04.json'
# 从文件中加载日志数据
log_data = load_log_data(log_file_path)


def main():
    start_carla()
    start_Autoware()
    
    client = carla.Client("127.0.0.1",2000)
    

    world=load_world()

    # 设置天气
    weather_params = carla.WeatherParameters(
        cloudiness=log_data['mission_setup']['weather']['cloudiness'],
        precipitation=log_data['mission_setup']['weather']['precipitation'],
        precipitation_deposits=log_data['mission_setup']['weather']['precipitation_deposits'],
        sun_altitude_angle=log_data['mission_setup']['weather']['sun_altitude_angle'],
        #fog_density=log_data['mission_setup']['weather']['fog_density'],
        #wetness=log_data['mission_setup']['weather']['wetness']
    )
    world.set_weather(weather_params)   
    

    actors=find_all_actor(world)
    victim=get_Autoware(world,actors)
    victim_location,victim_rotation=get_pos(victim)
    attacker,npc=load_npc(world,victim_location)
    history_commands = log_data['attack_commands']


    random_exec_command(history_commands,world,attacker,victim,npc)


    shutdown_carla()
    shutdown_Autoware()
    
    



if __name__ == '__main__':
    while True:
        try:
            main()
            time.sleep(20)
        except KeyboardInterrupt:
            shutdown_carla()
            shutdown_Autoware()
            break
        except Exception as e:
            print(f"运行失败，错误信息：{e}")
            shutdown_carla()
            shutdown_Autoware()
            break