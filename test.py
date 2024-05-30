import acero_main
from acero_main import *
from send_message import *
import until
from until import *
import datetime
from attack_logging import *
import os

def main():

    start_carla()
    start_Autoware()

    pid=os.getpid()
    folder_path = '/home/test/carla-autoware-universe/op_carla_038/test'
    file_path = os.path.join(folder_path, 'process_id.txt')
    with open(file_path,"w") as file:
        file.write(str(pid))

    world=load_world()
    weather=set_weather(world)
    actors=find_all_actor(world)
    victim=get_Autoware(world,actors)
    victim_location,victim_rotation=get_pos(victim)

    attacker,npc=load_npc(world,victim_location)

   
    starttime = time.time()
    trajectory,attack_commands,rewinding_details=trajectory_generation(world,attacker,victim,npc,weather)
    endtime = time.time()

    attack_car_detail = vehicle_details("vehicle.tesla.model3", 0, 0, trajectory)
    victim_car_detail = vehicle_details("vehicle.toyota.prius", 0, 0, trajectory=None)
    stopped_car_detail = vehicle_details("vehicle.tesla.cybertruck", 0, 0, trajectory=None)
    agent_list = [stopped_car_detail]
    setup = mission_setup(weather, agent_list, None)
    duration = mission_duration(None, endtime-starttime)

    global ATTACK_SUCCESS
    attlogger("C002", acero_main.ATTACK_SUCCESS, setup, duration, victim_car_detail, attack_car_detail, attack_commands, rewinding_details=rewinding_details)
    acero_main.ATTACK_SUCCESS =  False
    #time.sleep(10)
    
    shutdown_carla()
    shutdown_Autoware()
    

if __name__ == '__main__':
    
    while True:


        try:
            main()
            time.sleep(10)
        except KeyboardInterrupt:
            shutdown_carla()
            shutdown_Autoware()
            break
        except Exception as e:
            print(f"运行失败，错误信息：{e}")
            shutdown_carla()
            shutdown_Autoware()
