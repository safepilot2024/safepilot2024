import carla
import random
import time
import threading
from until import *
from send_message import *
import os
import datetime
from attack_logging import *

global WRONGD

#检验无误
#根据指导向量guide生成4条候选指令
def candidate_command_generation(counter, guide):

    # Candidates vehicle commands
    candidate_vehicle_commands = []

    for i in range(0,4):
        command = [0,0]
        if(counter==0):
            command[0]=random.uniform(0.5,1)
            command[1]=random.uniform(-0.4,0.4)
        elif(counter==1):
            command[0]=random.uniform(0.5,0.8)
            command[1]=random.uniform(-0.4,0.4)
        else:
            if(guide[0]<0):#x轴的间距变小了 攻击车应该加速
                command[0]=random.uniform(0.4,0.8)
            else:
                command[0]=random.uniform(-0.4,0.4)
            
            if(guide[1]>0):#y轴的间距变小了 攻击车应该左转
                command[1]=random.uniform(-2/5,-1/5)
            else:
                command[1]=random.uniform(1/5,2/5)                

        candidate_vehicle_commands.append(command) 
        print("candidate_vehicle_commands",i," = ",command)

  
    return candidate_vehicle_commands

#检验无误
#执行四条候选指令 执行后按鲁棒性评分从低到高排序
def command_generation(counter, guide,history_commands,world,attacker,victim,npc,weather,vic_traj,att_traj):
    candidate_vehicle_commands = candidate_command_generation(counter, guide)
    rob_list = []
    i = 0
    for command in candidate_vehicle_commands:
        
        temp_rob = -2
        while temp_rob == -2:
            #打印当前正在评估的命令，使用特定的颜色代码来高亮显示。
            print("this is counter ",counter," command ",i)
            print("\033[93m{Command:", command, "}\033[0m\n")
            #把攻击车，受害车，npc，代理的状态回溯到特定的状态
            attacker,victim,npc,world=rewind_scene(world,weather,attacker,victim,npc,history_commands)
            #攻击车执行指令
            temp_rob = exec_command(attacker,victim,command,world,npc,history_commands,vic_traj,att_traj)
            time.sleep(1)

        
        rob_list.append(temp_rob)
        i+=1
    
    # 使用 zip 将两个列表组合成一个，然后根据 rob_list 的值排序
    combined = zip(candidate_vehicle_commands, rob_list)
    sorted_combined = sorted(combined, key=lambda x: x[1])
    # “解压”排序后的列表回两个单独的列表
    sorted_candidate_vehicle_commands, sorted_rob_list = zip(*sorted_combined)
    # 将结果从元组转换回列表
    sorted_candidate_vehicle_commands = list(sorted_candidate_vehicle_commands)
    sorted_rob_list = list(sorted_rob_list)

    candidate_vehicle_commands = sorted_candidate_vehicle_commands
    rob_list = sorted_rob_list
    return candidate_vehicle_commands,rob_list

#执行5轮循环
def trajectory_generation(world,attacker,victim,npc,weather):
    #获得受害车与攻击车的x，y坐标 作为列表的第一个元素
    vic_traj, att_traj = [get_state(victim)], [get_state(attacker)]
    #攻击者的命令
    history_commands = []
    #回溯的详细信息
    rewinding_details = []
    #计数器
    counter = 0
    #指导元组初始化
    guide = [1, -1]#改了一下 试试效果
    all_candidate_vehicle_commands = [0,0,0,0,0]
    all_rob_list = [0,0,0,0,0]


    #读取这两个全局向量的值
    global ATTACK_SUCCESS,COLLISION_OBJECT

    #只要攻击没成功且轮数小于5
    while not ATTACK_SUCCESS and  counter<5:
        #输出轮数
        print("\033[92m>>>>This is counter {}\033[0m".format(counter))

        #如果这轮鲁棒性为0 证明这轮没有指令（没生成过 或者被清空了） 则生成一轮指令
        #不满足这个if 则代表当前轮有指令 是因为遇到了下一轮全是inf后回退得到的
        if all_rob_list[counter] == 0:
            history_commands = []
            if counter!=0:
                for i in range(0,counter):
                    history_commands.append(all_candidate_vehicle_commands[i][0])      
                
            candidate_vehicle_commands,rob_list=command_generation(counter, guide,history_commands,world,attacker,victim,npc,weather,vic_traj,att_traj)
            print("this is counter ",counter)
            for i in range(0,len(rob_list)):
                print ("rob",i," = ",rob_list[i],"commands",i," = ",candidate_vehicle_commands[i])
            
            all_candidate_vehicle_commands[counter] = candidate_vehicle_commands
            all_rob_list[counter] = rob_list

        #如果攻击成功了
        if all_rob_list[counter][0] == -1:
            history_commands = []
            for i in range(0,counter+1):
                history_commands.append(all_candidate_vehicle_commands[i][0])    
            return att_traj,history_commands,rewinding_details

        #重启carla autoware
        shutdown_carla()
        shutdown_Autoware()
        time.sleep(10)
        start_carla()
        start_Autoware()
        world=load_world()
        world.set_weather(weather)
        actors=find_all_actor(world)
        victim=get_Autoware(world,actors)
        victim_location,victim_rotation=get_pos(victim)
        attacker,npc=load_npc(world,victim_location)

        #如果当前轮鲁棒性最小值不为inf 即四条指令中存在指令鲁棒性不为inf 则执行鲁棒性最低的指令 然后记录位置用于生成guide 
        if all_rob_list[counter][0]!=float('inf'):  
            print("all_rob_list[counter][0]!=inf")   
            # time.sleep(10)
            attacker,victim,npc,world=rewind_scene(world,weather,attacker,victim,npc,history_commands)
            exec_command(attacker,victim,all_candidate_vehicle_commands[counter][0],world,npc,history_commands,vic_traj,att_traj,save_traj=True)
            RPtbefore   =  [att_traj[counter-1][0]-vic_traj[counter-1][0],att_traj[counter-1][1]-vic_traj[counter-1][1]]
            RPtafter    =  [att_traj[counter][0]-vic_traj[counter][0],att_traj[counter][1]-vic_traj[counter][1]]
            guide[0] = RPtafter[0]-RPtbefore[0]
            guide[1] = RPtafter[1]-RPtbefore[1]            
            counter+=1
            #重启carla autoware
            shutdown_carla()
            shutdown_Autoware()
            time.sleep(10)
            start_carla()
            start_Autoware()
            world=load_world()
            world.set_weather(weather)
            actors=find_all_actor(world)
            victim=get_Autoware(world,actors)
            victim_location,victim_rotation=get_pos(victim)
            attacker,npc=load_npc(world,victim_location)            
            continue
        #如果当前轮鲁棒性最小值为inf 即四条指令鲁棒性都为inf 则清空当前轮 然后回到上一轮 把上一轮的鲁棒性最小的指令鲁棒性变成inf 然后重新排序
        elif all_rob_list[counter][0]==float('inf'):
            print("all_rob_list[counter][0]==inf")   
            #清空当前轮指令与鲁棒性评分
            all_rob_list[counter] = 0
            all_candidate_vehicle_commands[counter]=0
            #回退到上一轮
            counter-=1
            #把上一轮的第一条指令鲁棒性评分置为inf
            all_rob_list[counter][0] = float('inf')
            #把上一轮重新排序
            candidate_vehicle_commands = all_candidate_vehicle_commands[counter]
            rob_list = all_rob_list[counter]
            combined = zip(candidate_vehicle_commands, rob_list)
            sorted_combined = sorted(combined, key=lambda x: x[1])
            sorted_candidate_vehicle_commands, sorted_rob_list = zip(*sorted_combined)
            sorted_candidate_vehicle_commands = list(sorted_candidate_vehicle_commands)
            sorted_rob_list = list(sorted_rob_list)    
            candidate_vehicle_commands = sorted_candidate_vehicle_commands
            rob_list = sorted_rob_list    
            all_candidate_vehicle_commands[counter] = candidate_vehicle_commands
            all_rob_list[counter] = rob_list
            #把上一轮之前的第一条指令生成的坐标扔掉
            vic_traj.pop()
            att_traj.pop()
            #重新计算guide
            RPtbefore   =  [att_traj[counter-1][0]-vic_traj[counter-1][0],att_traj[counter-1][1]-vic_traj[counter-1][1]]
            RPtafter    =  [att_traj[counter][0]-vic_traj[counter][0],att_traj[counter][1]-vic_traj[counter][1]]
            guide[0] = RPtafter[0]-RPtbefore[0]
            guide[1] = RPtafter[1]-RPtbefore[1]  


    history_commands = []
    for i in range(0,counter):
        history_commands.append(all_candidate_vehicle_commands[i][0])      
    
    print(att_traj)
    print(history_commands)
    return att_traj,history_commands,rewinding_details


def run_autoware(victim):
    #记录当前时间
    #打印正在执行受害者车辆的命令
    print("exec current victim")
    destination=get_destination_transform(victim)
    ros2_transform=carla_to_ros2(destination)
    send_destination_2_autoware(ros2_transform)

#只要回溯场景 不执行任何命令
def rewind_scene(world,weather,attacker,victim,npc,history_commands):
    global REWIND

    print("\033[91mREWIND!\033[0m")

    #打印 回溯
    print("wait for autoware finish last command")
    speed=check_autoware_speed(victim)
    while speed > 2:
        speed=check_autoware_speed(victim)
        time.sleep(0.5) 
 
    time.sleep(5)    
    print("Reset Autoware init position and posture")
    pos=Init_Autoware_postion()
    reset_autoware_position(victim,pos)
    print("rewind")
    
    attacker.destroy()
    npc.destroy()
    
    time.sleep(5)
    #将REWIND 设置为 False，表明回溯操作已完成
    REWIND=False
    ##生成新的受害车、攻击车、代理、npc
    world=load_world()
    world.set_weather(weather)
    actors=find_all_actor(world)
    victim=get_Autoware(world,actors)
    victim_location,victim_rotation=get_pos(victim)
    attacker,npc=load_npc(world,victim_location)
    print("Finish rewind")
    #返回攻击车、受害车、代理、npc
    return attacker, victim,npc,world

#执行历史指令干了什么：让受害车动 ， 执行history_commands中的每一条指令 每个1s
#run_autoware不要多次发送 每轮场景只发送一次 如果受害车没动就再发一次 还不动就重启autoware和carla

    

def exec_command(attacker,victim,command,world,npc,history_commands,vic_traj = [],att_traj = [],save_traj=False):
    #攻击车是否撞车:False
    global ATTACK_COLLISION_OBJECT
    ATTACK_COLLISION_OBJECT=False
    #从world中获取地图
    map=world.get_map()

    print("Reset Autoware init position and posture")
    pos=Init_Autoware_postion()
    reset_autoware_position(victim,pos)
    time.sleep(5)

    run_autoware(victim)

    #输出执行命令前的鲁棒性评分
    # print("Before Exec", robustness_calculation(victim, npc,map, TTC=True, DIST=False))
    #检查攻击者车辆是否发生碰撞，并将结果存储在 collision_sensor 中
    attacker_collision_sensor=check_collision_attacker(attacker,world)
    #这是一个碰撞传感器 只要撞了就ATTACK_COLLISION_OBJECT=True
    victim_collision_sensor=check_collision_victim(victim,attacker,world)

    speed=check_autoware_speed(victim)
    start=time.time()

    if_resend_message = False
    while speed<=2:
        speed=check_autoware_speed(victim)
        time.sleep(0.5)    
        if if_resend_message == False and time.time()-start>10:
            run_autoware(victim)
            if_resend_message = True
            print("Resend message!")
            start = time.time()
        elif if_resend_message ==True and time.time()-start>10:
            print("Autoware Wrong!! Rewind!!")
            
            #销毁碰撞传感器
            for sensor in attacker_collision_sensor:
                sensor.destroy()  
            for sensor in victim_collision_sensor:
                sensor.destroy()              
            shutdown_carla()
            shutdown_Autoware()     
            time.sleep(10)
            start_carla()
            start_Autoware()
            
            world=load_world()
            weather=set_weather(world)
            actors=find_all_actor(world)
            victim=get_Autoware(world,actors)
            victim_location,victim_rotation=get_pos(victim)
            attacker,npc=load_npc(world,victim_location)

            return -2

    print("Victim Run!")   
    time.sleep(4)
    print("exec current attacker")
    if history_commands:
        # time.sleep(10)
        for history_command in history_commands:
            attacker.apply_control(carla_command(history_command))
            print("exec ",history_command)
            time.sleep(1.5)    

    
    attacker.apply_control(carla_command(command))
    print("exec ",command)
    time.sleep(1.5)

    temp_rob = robustness_calculation(victim, npc,map, TTC=True, DIST=False)
    if save_traj==True:
        vic_traj.append(get_state(victim))
        att_traj.append(get_state(attacker))
    attacker.apply_control(carla_command([-0.5,0]))    
    
    time.sleep(10)

    #销毁碰撞传感器
    for sensor in attacker_collision_sensor:
        sensor.destroy()
    
    #overspeed = check_os(attacker)
   
    wrongdirection = check_wd(attacker, map)

    #输出是否攻击车超速、方向错误、碰撞
    #print("Overspeed: ", overspeed)
    print("Wrong Direction: ", wrongdirection)
    print("Attacker Collision:",ATTACK_COLLISION_OBJECT)
    global ATTACK_SUCCESS, REWIND
    # global REWIND
    #输出是否攻击成功
    print("Attack Success: ", ATTACK_SUCCESS)

    for sensor in victim_collision_sensor:
        sensor.destroy()

    if wrongdirection == True or ATTACK_COLLISION_OBJECT == True:
        print("robustness is ",float('inf'))
    elif ATTACK_SUCCESS == True and ATTACK_COLLISION_OBJECT == False:
        print("robustness is -1")
    else:
        print("robustness is ",temp_rob)

    #如果攻击成功了 就返回-1
    if ATTACK_SUCCESS == True and ATTACK_COLLISION_OBJECT == False:
        return -1
    #035 加入
    # if wrongdirection == True or REWIND == True or ATTACK_COLLISION_OBJECT == True:
    if wrongdirection == True or ATTACK_COLLISION_OBJECT == True:
        return float('inf')
    else:
        return temp_rob

def robustness_calculation(acar, vcar,map, TTC=False, DIST=False):
    #计算碰撞时间 如果无法碰撞就返回无穷大
    if TTC:
        ttc = time_to_collision(acar, vcar)
        if ttc == -1:
            return float('inf')
        
        return ttc
    #计算距离 这玩意有-1？？？ 不知道为什么会有这个if 怀疑是直接复制的之前的ttc
    if DIST:
        dist = Dist(vcar, map)
        if dist == -1:
            return float('inf')
        return dist

def time_to_collision(object_a, object_b):
    """
    Calculate the TTC of between two objects
    (Need to consider the direction of the object)
    """

    # 1. Decide which one is the front object. Here we assume the front direction is to 'positive_x' direction for simplicity
    if object_a.get_transform().location.x > object_b.get_transform().location.x:
        front_object = object_a
        back_object = object_b
    else:
        front_object = object_b
        back_object = object_a
    
    # 2. Decide which one is the left object. Here we assume the right direction is to 'positive_y' direction for simplicity
    if object_a.get_transform().location.y < object_b.get_transform().location.y:
        left_object = object_a
        right_object = object_b
    else:
        left_object = object_b
        right_object = object_a
    
    # 3. Decide the potential collision part
    most_left_point = right_object.get_transform().location.y - right_object.bounding_box.extent.y
    most_right_point = left_object.get_transform().location.y + left_object.bounding_box.extent.y

    most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.x
    most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.x


    different_direction = False
    if abs(front_object.get_transform().rotation.yaw - back_object.get_transform().rotation.yaw) > 0.45:
        different_direction = True
        most_back_point = front_object.get_transform().location.x - front_object.bounding_box.extent.y
        most_front_point = back_object.get_transform().location.x + back_object.bounding_box.extent.y

    if (back_object.get_velocity().x - front_object.get_velocity().x)<=0:
        return 99999

    # If collision is not possible, return -1
    # 1. Check if the front object is in the potential collision area
    # 2. Check if the back object has a higher speed
    if different_direction and front_object.get_velocity().x < back_object.get_velocity().x:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)
    # elif most_left_point < most_right_point or front_object.get_velocity().x >= back_object.get_velocity().x:
    #035 改了这里
    elif most_left_point > most_right_point or front_object.get_velocity().x >= back_object.get_velocity().x:    
        return 99999
    else:
        return (most_back_point-most_front_point)/(back_object.get_velocity().x - front_object.get_velocity().x)


#计算距离 标过了
def Dist(obj, map):
    """
    Calculate the distance between two objects
    """

    # 1. Get the nearst way point of vehicle
    obj_waypoint = map.get_waypoint(obj.get_location(), project_to_road=True)
    
    # 2. Calculate the distance between the vehicle and the cloest lane mark
    dist = obj_waypoint.lane_width/2 - abs(obj.get_location().y - obj_waypoint.transform.location.y)

    return dist

def check_collision_attacker(attacker, world):
    def on_collision(event):
        global ATTACK_COLLISION_OBJECT
        ATTACK_COLLISION_OBJECT = True
        global REMAKE
        REMAKE = True
        # print("攻击车撞了！！！！！")

    # 从carla中找到碰撞传感器的蓝图并返回为bp
    bp = world.get_blueprint_library().find('sensor.other.collision')

    # 定义车辆的四个角的位置
    # sensor_offsets = [
    #     carla.Transform(carla.Location(x=2.5, y=0.0, z=1.0)),  # 前端
    #     carla.Transform(carla.Location(x=-2.5, y=0.0, z=1.0)), # 后端
    #     carla.Transform(carla.Location(x=0.0, y=2.5, z=1.0)),  # 左侧
    #     carla.Transform(carla.Location(x=0.0, y=-2.5, z=1.0))  # 右侧
    # ]

    sensor_offsets = [
        carla.Transform(carla.Location(x=0.0, y=0.0, z=1.0)),  # 前端
    ]

    # 为每个位置创建一个碰撞传感器并附加到攻击车辆
    collision_sensors = []
    for offset in sensor_offsets:
        sensor = world.spawn_actor(bp, offset, attach_to=attacker)
        sensor.listen(on_collision)
        collision_sensors.append(sensor)

    # 返回所有创建的碰撞传感器
    return collision_sensors

def check_collision_victim(victim, attacker, world):
    # 添加一个标志变量来跟踪是否已经输出过碰撞提示信息
    collision_handled = False

    def on_collision(event):
        nonlocal collision_handled  # 使用nonlocal关键字来修改外部函数中的变量
        if collision_handled:  # 如果已经处理过碰撞，直接返回
            return

        if event.other_actor.id == attacker.id:
            print("-------Collision with attacker-------")
        else:
            global ATTACK_SUCCESS
            ATTACK_SUCCESS = True
            # print("ATTACK_SUCCESS :",ATTACK_SUCCESS)
            print("-------Victim collision--------")
            global COLLISION_OBJECT
            COLLISION_OBJECT = event.other_actor.id
            # print("COLLISION_OBJECT :",COLLISION_OBJECT)
           

        collision_handled = True  # 设置标志变量，表示已经处理过碰撞

    # 从carla中找到碰撞传感器的蓝图并返回为bp
    bp = world.get_blueprint_library().find('sensor.other.collision')

    # 定义车辆的四个角的位置
    # sensor_offsets = [
    #     carla.Transform(carla.Location(x=2.5, y=0.0, z=1.0)),  # 前端
    #     carla.Transform(carla.Location(x=-2.5, y=0.0, z=1.0)), # 后端
    #     carla.Transform(carla.Location(x=0.0, y=2.5, z=1.0)),  # 左侧
    #     carla.Transform(carla.Location(x=0.0, y=-2.5, z=1.0))  # 右侧
    # ]
    sensor_offsets = [
        carla.Transform(carla.Location(x=0.0, y=0.0, z=1.0)),  #
    ]
    
    # 为每个位置创建一个碰撞传感器并附加到受害车辆
    collision_sensors = []
    for offset in sensor_offsets:
        sensor = world.spawn_actor(bp, offset, attach_to=victim)
        sensor.listen(on_collision)
        collision_sensors.append(sensor)

    # 返回所有创建的碰撞传感器
    return collision_sensors