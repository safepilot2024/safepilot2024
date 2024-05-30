import sys
sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla/dist/carla-0.9.13-py3.7-linux-x86_64.egg')
import carla
from carla import Location, Rotation, Transform
import random
import time
import math
from config import *
import Acero
from Acero import *
import execute
from execute import *
from attack_logging import *

sys.path.append('/home/test/carla/CARLA_0.9.13/PythonAPI/carla')
from agents.navigation.behavior_agent import BehaviorAgent  # pylint: disable=import-error
from agents.navigation.basic_agent import BasicAgent  # pylint: disable=import-error


client = carla.Client('localhost', 2000)
client.replay_file('/home/test/文档/carlalog/20240423_154913.log',0,0,0)
