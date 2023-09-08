#!/usr/bin/python3
import rospy, rospkg, sys, numpy as np
sys.dont_write_bytecode = True

from sensor_msgs.msg import Joy
from std_msgs.msg import Empty
from geometry_msgs.msg import Twist

from std_srvs.srv import Empty as EmptySrv

class Joystick:
    def __init__(self, model, topic):
        
        mapping = np.load(rospkg.RosPack().get_path('drone_simulation')+'/scripts/modules/joysticks.npz', allow_pickle=True)
        self.buttons_keys, self.axes_keys = mapping[model].item().values()
        
        self.buttons = dict.fromkeys(self.buttons_keys, 0)
        self.axes = dict.fromkeys(self.axes_keys, 0.0)
        
        rospy.Subscriber(topic, Joy, self.joystick_callback, queue_size=1)
        self.observers = []
        
    def joystick_callback(self, msg:Joy):
        buttons_values = msg.buttons
        axes_values = msg.axes
        
        self.buttons = dict(zip(self.buttons_keys, buttons_values))
        self.axes = dict(zip(self.axes_keys, axes_values))
        
        self.notify_observers()
        
    def register_observer(self, observer):
        self.observers.append(observer)
        
    def notify_observers(self):
        for observer in self.observers:
            observer.update()

class JoystickParrot:
    def __init__(self, model, topic):
        self.joystick = Joystick(model=model, topic=topic)
        self.joystick.register_observer(self)
        
        self.takeoff = rospy.Publisher('/bebop/takeoff', Empty, queue_size=1)
        self.land = rospy.Publisher('/bebop/land', Empty, queue_size=1)
        self.reset = rospy.Publisher('/bebop/reset', Empty, queue_size=1)
        self.cmd_vel = rospy.Publisher('/bebop/cmd_vel', Twist, queue_size=1)
        
    def update(self):
        
        if self.joystick.buttons['Y']:
            self.takeoff.publish(Empty())
        
        if self.joystick.buttons['A']:
            self.land.publish(Empty())
            
        if self.joystick.buttons['BACK']:
            self.reset_world()
            self.reset.publish(Empty())
        
        cmd_vel = Twist()
        cmd_vel.linear.x = self.joystick.axes['LV']
        cmd_vel.linear.y = self.joystick.axes['LH']
        cmd_vel.linear.z = self.joystick.axes['RV']
        cmd_vel.angular.z = self.joystick.axes['RH']
        self.cmd_vel.publish(cmd_vel)
        
    def reset_world(self):
        self.reset.publish(Empty())
        self.hovercito()
        rospy.wait_for_service('/gazebo/reset_world')
        try:
            reset_world = rospy.ServiceProxy('/gazebo/reset_world', EmptySrv)
            reset_world()
        except rospy.ServiceException as e:
            rospy.logerr(f"Service call failed: {e}")
        
    def hovercito(self):
        cmd_vel = Twist()
        cmd_vel.linear.x = 0.0
        cmd_vel.linear.y = 0.0
        cmd_vel.linear.z = 0.0
        cmd_vel.angular.z = 0.0
        self.cmd_vel.publish(cmd_vel)
        
def main():
    rospy.init_node('joystick')
    # Available models: 'USB', 'Xbox360', 'XboxChinese', 'XboxOne', 'Pro'
    node = JoystickParrot(model='Xbox360', topic='/bebop2/joy')
    rospy.spin()

if __name__ == '__main__':
    main()