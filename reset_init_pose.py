import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import math
import carla
import numpy as np

class SetInitialPoseNode(Node):
    def __init__(self,transform):
        super().__init__('set_initial_pose_node')
        self.transform = transform
        self.initial_pose_pub = self.create_publisher(PoseWithCovarianceStamped, '/initialpose3d', 10)
        self.timer = self.create_timer(1, self.publish_initial_pose)


    def publish_initial_pose(self):
        initial_pose_msg = PoseWithCovarianceStamped()
        ros2_transform = self.carla_to_ros2()

        # 设置初始姿态信息
        initial_pose_msg.pose.pose.position.x = ros2_transform["x"]
        initial_pose_msg.pose.pose.position.y = ros2_transform["y"]
        initial_pose_msg.pose.pose.position.z = ros2_transform["z"]
        initial_pose_msg.pose.pose.orientation.x = ros2_transform["qx"]
        initial_pose_msg.pose.pose.orientation.y = ros2_transform["qy"]
        initial_pose_msg.pose.pose.orientation.z = ros2_transform["qz"]
        initial_pose_msg.pose.pose.orientation.w = ros2_transform["qw"]

        self.initial_pose_pub.publish(initial_pose_msg)
        self.get_logger().info('Published initial pose')

    def carla_to_ros2(self):
        ros2_transform = {}

        ros2_transform["x"] = self.transform.location.x
        ros2_transform["y"] = -self.transform.location.y
        ros2_transform["z"] = self.transform.location.z

        roll = math.radians(self.transform.rotation.roll)
        pitch = -math.radians(self.transform.rotation.pitch)
        yaw = -math.radians(self.transform.rotation.yaw)
        qx = np.sin(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) - np.cos(roll / 2) * np.sin(pitch / 2) * np.sin(
            yaw / 2)
        qy = np.cos(roll / 2) * np.sin(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.cos(pitch / 2) * np.sin(
            yaw / 2)
        qz = np.cos(roll / 2) * np.cos(pitch / 2) * np.sin(yaw / 2) - np.sin(roll / 2) * np.sin(pitch / 2) * np.cos(
            yaw / 2)
        qw = np.cos(roll / 2) * np.cos(pitch / 2) * np.cos(yaw / 2) + np.sin(roll / 2) * np.sin(pitch / 2) * np.sin(
            yaw / 2)
        ros2_transform["qx"] = qx
        ros2_transform["qy"] = qy
        ros2_transform["qz"] = qz
        ros2_transform["qw"] = qw

        return ros2_transform

def main(args=None):
    rclpy.init(args=args)
    set_initial_pose_node = SetInitialPoseNode()
    rclpy.spin_once(set_initial_pose_node)
    #rclpy.spin(set_initial_pose_node)
    set_initial_pose_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
