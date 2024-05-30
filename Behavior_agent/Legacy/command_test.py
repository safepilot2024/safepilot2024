
import sys
sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
import threading

import sys
sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
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

sys.path.append('/home/reasult/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error


candidate_vehicle_commands = []

def cam_chase_player(player, spectator):
    location = player.get_location()
    rotation = player.get_transform().rotation

    # 放到车正上方
    # 假设我们不需要调整x和y，因为我们希望摄像头直接位于车辆的正上方
    # 只需要调整z轴（高度），以确保摄像头位于车辆上方一定高度
    height_above_car = 45  # 摄像头距离车辆的高度，可以根据需要调整

    location.z += height_above_car

    # 设置摄像头的旋转使其直接向下看
    # 旋转角度需要设置为向下看，所以将俯仰角（pitch）设置为-90度（直下），偏航角（yaw）和翻滚角（roll）不变
    rotation.pitch = -90  # 向下看
    # rotation.yaw = 保持不变，根据车辆当前的方向
    # rotation.roll = 保持不变，一般情况下摄像头不需要翻滚

    # 应用变换
    spectator.set_transform(
        carla.Transform(location, rotation)
    )


def carla_command(command):
    # Convert the command to carla command
    if command[0] < 0:  # brake
        return carla.VehicleControl(throttle=0, steer= command[1], brake=abs(command[0]))
    else:   # Throttle
        return carla.VehicleControl(throttle=command[0], steer=command[1], brake=0)
    
def control_npc(attacker,candidate_vehicle_commands):
    for control in candidate_vehicle_commands:
        attacker.apply_control(carla_command(control))
        time.sleep(0.5)


def control_agent(agent,victim):
    time.sleep(0.5)
    start_time = time.time()
    while time.time() - start_time<5:
        
        control = agent.run_step()
        victim.apply_control(control)


def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0) # 设置超时时间

        # 获取世界
    town="Town03"
    client.load_world(town)
    world = client.get_world()
    spectator=world.get_spectator()
    map=world.get_map()


    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]      ## only for agent

    player_bp=blueprint_library.filter("vehicle.tesla.model3")[0]



    spawn_point=Transform(Location(x=-30, y=-195, z=0.200000), Rotation(pitch=0.000000, yaw=0, roll=0.000000))
    attack_vehicle_pos=Transform(Location(x=-20, y=-198, z=0.200000), Rotation(pitch=0.000000, yaw=0, roll=0.000000))
    bp = world.get_blueprint_library().find('sensor.other.collision')

    victim=world.spawn_actor(vehicle_bp,spawn_point)
    attacker=world.spawn_actor(player_bp,attack_vehicle_pos)


    agent=BehaviorAgent(victim,behavior='normal')

    cam_chase_player(victim,spectator)


    current_transform  =victim.get_transform()
    current_location = current_transform.location
    current_rotation = current_transform.rotation
    forward_vector = carla.Location(x=math.cos(math.radians(current_rotation.yaw)), y=math.sin(math.radians(current_rotation.yaw)))
    destination_location = carla.Location(x=current_location.x + forward_vector.x * 150, y=current_location.y , z=current_location.z)
    agent.set_destination(destination_location)
    #control = carla.VehicleControl(throttle=1, steer=0.15, brake=0.0)
    
    #directions = [(0.2,0.3),(0.1,0.2),(-0.1,0.1),(-0.1,-0.2),(-0.3, -0.2)]
    directions = [(-1 / 3, 1 / 3), (1 / 3, 1), (-1, -1 / 3)]
    #thros = [(-1/2, 0), (-1/2, 1/2), (1/2, 1)] 

    for dir in directions:
                
                steer = random.uniform(dir[0], dir[1])
                throttle = random.uniform(0.1,0.5)
                #if counter==2:
                    #steer = random.uniform(dir[0], dir[1])
                    #throttle = random.uniform(-1,-0.5)
                # print((throttle, steer))
                candidate_vehicle_commands.append((throttle, steer))

    print(candidate_vehicle_commands)

    thread_npc = threading.Thread(target=control_npc,args=(attacker,candidate_vehicle_commands))
    thread_agent = threading.Thread(target=control_agent,args=(agent,victim))


    thread_npc.start()
    thread_agent.start()



    thread_npc.join()
    thread_agent.join()


if __name__ == '__main__':
    
    try:
        while True:
            time.sleep(5)
            main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)