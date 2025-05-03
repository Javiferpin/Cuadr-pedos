#!/usr/bin/env python

import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from math import atan2, sqrt
from tf.transformations import euler_from_quaternion

# Inicialización de variables
waypoints = [(1, 0), (2, 0), (2.5, 0), (2.5, -0.5), (3.5, -0.5) y (6, -0.6)]
current_waypoint_index = 0

# Initialisation
rospy.init_node('waypoint_navigation', anonymous=True)
cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

# Variables pour la position et l'inclinaison
current_x = 0.0
current_y = 0.0
current_theta = 0.0
pitch_angle = 0.0  # Nouvelle variable

# Callback Odometry
def odom_callback(msg):
    global current_x, current_y, current_theta
    current_x = msg.pose.pose.position.x
    current_y = msg.pose.pose.position.y
    orientation_q = msg.pose.pose.orientation
    _, _, current_theta = euler_from_quaternion([orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w])

# Callback IMU pour lire l'inclinaison
def imu_callback(msg):
    global pitch_angle
    orientation_q = msg.orientation
    roll, pitch, yaw = euler_from_quaternion([orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w])
    pitch_angle = pitch  # Inclinaison avant/arrière

# Fonction pour se déplacer vers un waypoint avec adaptation sur pente
def move_to_waypoint(waypoint):
    global current_x, current_y, current_theta, pitch_angle

    dx = waypoint[0] - current_x
    dy = waypoint[1] - current_y
    distance = sqrt(dx**2 + dy**2)

    angle_to_goal = atan2(dy, dx)
    angle_diff = angle_to_goal - current_theta

    # Normaliser angle
    while angle_diff > 3.14159:
        angle_diff -= 2 * 3.14159
    while angle_diff < -3.14159:
        angle_diff += 2 * 3.14159

    cmd = Twist()

    # 1. S'orienter si nécessaire
    if abs(angle_diff) > 0.4:
        cmd.linear.x = 0.0
        cmd.angular.z = 0.4 * angle_diff

    else:
        # 2. Avancer en fonction de la pente
        base_speed = 0.1
        variable_speed = 0.05 * distance
        speed = min(base_speed + variable_speed, 0.12)  # Normal

        # 🎯 Ajustement selon l'inclinaison détectée
        if abs(pitch_angle) > 0.25:  # environ 15 degrés
            speed *= 0.7  # ralentir un peu pour ne pas glisser

        if abs(pitch_angle) > 0.4:  # environ 23 degrés
            speed *= 1.5  # forcer un boost pour grimper

        if speed > 0.18:
            speed = 0.18  # pas plus rapide que ça pour rester stable

        cmd.linear.x = speed
        cmd.angular.z = 0.2 * angle_diff

    cmd_vel_pub.publish(cmd)

# Boucle principale
def navigate():
    global current_waypoint_index

    rospy.Subscriber('/odom', Odometry, odom_callback)
    rospy.Subscriber('/imu', Imu, imu_callback)  # Souscription à l'IMU aussi

    rate = rospy.Rate(10)

    while not rospy.is_shutdown():
        if current_waypoint_index >= len(waypoints):
            cmd_vel_pub.publish(Twist())
            rospy.loginfo("Tous les waypoints atteints. Robot arrêté.")
            break

        current_waypoint = waypoints[current_waypoint_index]
        move_to_waypoint(current_waypoint)

        dx = current_waypoint[0] - current_x
        dy = current_waypoint[1] - current_y
        distance = sqrt(dx**2 + dy**2)

        if distance < 0.1:
            rospy.loginfo(f"Waypoint {current_waypoint_index+1} atteint.")
            current_waypoint_index += 1

        rate.sleep()

if __name__ == '__main__':
    try:
        navigate()
    except rospy.ROSInterruptException:
        pass

