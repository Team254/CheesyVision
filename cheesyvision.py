#!/usr/bin/env python
# Copyright (c) 2014, Team 254
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, this
#       list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
#       THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#       ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#       WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#       DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#       ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#       (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#       LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#       ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#       (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#       SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#       The views and conclusions contained in the software and documentation are those
#       of the authors and should not be interpreted as representing official policies,
#       either expressed or implied, of the FreeBSD Project.

# ~~~~~~~~~~~~~~~~~~~~
# ~~~ CheesyVision ~~~
# ~~~~~~~~~~~~~~~~~~~~
#
# This Python script uses your laptop's webcam and OpenCV to allow an operator to
# signal which goal is hot during autonomous mode.  You can think of it as a poor
# man's Kinect, but one that does not need a USB port, power supply, or special
# hardware.
#
# Configure the script by following the instructions posted here:
# https://github.com/Team254/CheesyVision
#
# Then, set your team number below and you are good to go!
#
# To use, run the script and see that there are three boxes overlayed on the webcam
# image.  The top center box is for "calibration", and it constantly computes the
# average color inside of the box as a reference.  The other two boxes are used for
# signalling the hot goal.  Basically, if the left and right boxes are about the same
# color as the calibration box, we assume the goal is hot.  If the color is different,
# we assume the goal is not hot.  If you are wearing a colorful, solid shirt, you can
# just use your hands - watch how the widget indicates what it sees as you move your
# hands through the boxes.  Or, you might find that a brightly colored object that your
# operator holds works better for you.  Before the match starts, hold up your hands, and
# then drop the one that corresponds to the hot goal.  The information is then sent to
# the cRIO.
#
# (We found that the "default hot" strategy works best, because it forces you to double
#  check that the camera is working before the match.)
#
# There are 5 keys that you can use to tweak the performance of the app:
#  1. Escape quits.
#  2. W and S increment and decrement exposure (if your webcam supports this feature).
#     This is very useful if you find the image looks too washed out.
#  3. A and D increment and decrement the color threshold used to tell if the color is
#     different.
#
# Enjoy!
import numpy as np
import cv2 as cv
import socket
import time

# CHANGE THIS TO BE YOUR TEAM'S cRIO IP ADDRESS!
HOST, PORT = "10.2.54.2", 1180

# Name of displayed window
WINDOW_NAME = "CheesyVision"

# Width of the entire widget
WIDTH_PX = 1000

# Dimensions of the webcam image (it will be resized to this size)
WEBCAM_WIDTH_PX = 640
WEBCAM_HEIGHT_PX = 360

# The number of columns from the left of the widget where the image starts.
X_OFFSET = (WIDTH_PX - WEBCAM_WIDTH_PX)/2

# The location of the calibration rectangle.
CAL_UL = (X_OFFSET + WEBCAM_WIDTH_PX/2 - 20, 180)
CAL_LR = (X_OFFSET + WEBCAM_WIDTH_PX/2 + 20, 220)

# The location of the left rectangle.
LEFT_UL = (240 + X_OFFSET, 250)
LEFT_LR = (310 + X_OFFSET, 300)

# The location of the right rectangle.
RIGHT_UL = (WEBCAM_WIDTH_PX - 310 + X_OFFSET, 250)
RIGHT_LR = (WEBCAM_WIDTH_PX - 240 + X_OFFSET, 300)

# Constants for drawing.
BOX_BORDER = 3
CONNECTED_BORDER = 15

# This is the rate at which we will send updates to the cRIO.
UPDATE_RATE_HZ = 40.0
PERIOD = (1.0 / UPDATE_RATE_HZ) * 1000.0

def get_time_millis():
    ''' Get the current time in milliseconds. '''
    return int(round(time.time() * 1000))

def color_distance(c1, c2):
    ''' Compute the difference between two HSV colors.

    Currently this simply returns the "L1 norm" for distance,
    or delta_h + delta_s + delta_v.  This is not a very robust
    way to do it, but it has worked well enough in our tests.

    Recommended reading:
    http://en.wikipedia.org/wiki/Color_difference
    '''
    total_diff = 0
    for i in (0, 1, 2):
        diff = (c1[i]-c2[i])
        # Wrap hue angle...OpenCV represents hue on (0, 180)
        if i == 0:
            if diff < -90:
                diff += 180
            elif diff > 90:
                diff -= 180
        total_diff += abs(diff)
    return total_diff

def color_far(img, ul, lr):
    ''' Light up a bright yellow rectangle if the color distance is large. '''
    cv.rectangle(img, ul, lr, (0, 255, 255), -1)

def draw_static(img, connected):
    ''' Draw the image and boxes. '''
    bg = np.zeros((img.shape[0], WIDTH_PX, 3), dtype=np.uint8)
    bg[:,X_OFFSET:X_OFFSET+WEBCAM_WIDTH_PX,:] = img
    cv.rectangle(bg, LEFT_UL, LEFT_LR, (0, 255, 255), BOX_BORDER)
    cv.rectangle(bg, RIGHT_UL, RIGHT_LR, (0, 255, 255), BOX_BORDER)
    cv.rectangle(bg, CAL_UL, CAL_LR, (255, 255, 255), BOX_BORDER)
    if connected:
        cv.rectangle(bg, (0, 0), (bg.shape[1]-1, bg.shape[0]-1), (0, 255, 0), CONNECTED_BORDER)
    else:
        cv.rectangle(bg, (0, 0), (bg.shape[1]-1, bg.shape[0]-1), (0, 0, 255), CONNECTED_BORDER)
    return bg

def detect_color(img, box):
    ''' Return the average HSV color of a region in img. '''
    h = np.mean(img[box[0][1]+3:box[1][1]-3, box[0][0]+3:box[1][0]-3, 0])
    s = np.mean(img[box[0][1]+3:box[1][1]-3, box[0][0]+3:box[1][0]-3, 1])
    v = np.mean(img[box[0][1]+3:box[1][1]-3, box[0][0]+3:box[1][0]-3, 2])
    return (h,s,v)

def detect_colors(img):
    ''' Return the average colors for the calibration, left, and right boxes. '''
    cal = detect_color(img, (CAL_UL, CAL_LR))
    left = detect_color(img, (LEFT_UL, LEFT_LR))
    right = detect_color(img, (RIGHT_UL, RIGHT_LR))

    return cal, left, right

def main():
    cv.namedWindow(WINDOW_NAME, 1)

    # Open the webcam (should be the only video capture device present).
    capture = cv.VideoCapture(0)

    # The maximum difference in average color between two boxes to consider them
    # the same.  See color_distance.
    max_color_distance = 100
    last_max_color_distance = max_color_distance

    # Manually set the exposure, because a lot of webcam drivers will overexpose
    # the image and lead to poor separation between foreground and background.
    exposure = -4
    last_exposure = exposure
    capture.set(15, exposure)  # 15 is the enum value for CV_CAP_PROP_EXPOSURE

    # Keep track of time so that we can provide the cRIO with a relatively constant
    # flow of data.
    last_t = get_time_millis()

    # Are we connected to the server on the robot?
    connected = False
    s = None

    while 1:
        # Get a new frame.
        _, img = capture.read()

        # Flip it and shrink it.
        small_img = cv.flip(cv.resize(img, (WEBCAM_WIDTH_PX, WEBCAM_HEIGHT_PX)), 1)

        # Render the image onto our canvas.
        bg = draw_static(small_img, connected)

        # Get the average color of each of the three boxes.
        cal, left, right = detect_colors(cv.cvtColor(bg, cv.COLOR_BGR2HSV))

        # Get the difference between the left and right boxes vs. calibration.
        left_dist = color_distance(left, cal)
        right_dist = color_distance(right, cal)

        # Check the difference.
        left_on = left_dist < max_color_distance
        right_on = right_dist < max_color_distance

        # If we detect a hot goal, color that side of the widget.
        B = CONNECTED_BORDER-5
        if left_on:
            color_far(bg, (B, B), ((WIDTH_PX-WEBCAM_WIDTH_PX)/2-B, WEBCAM_HEIGHT_PX-B))
        if right_on:
            color_far(bg, ((WIDTH_PX+WEBCAM_WIDTH_PX)/2+B, B), (WIDTH_PX-B, WEBCAM_HEIGHT_PX-B))

        # Throttle the output
        cur_time = get_time_millis()
        if last_t + PERIOD <= cur_time:
            # Try to connect to the robot on open or disconnect
            if not connected:
                try:
                    # Open a socket with the cRIO so that we can send the state of the hot goal.
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                    # This is a pretty aggressive timeout...we want to reconnect automatically
                    # if we are disconnected.
                    s.settimeout(.1)
                    s.connect((HOST, PORT))
                except:
                    print "failed to reconnect"
                    last_t = cur_time + 1000
            try:
                # Send one byte to the cRIO:
                # 0x01: Right on
                # 0x02: Left on
                # 0x03: Both on
                write_bytes = bytearray()
                v = (left_on << 1) | (right_on << 0)
                write_bytes.append(v)
                s.send(write_bytes)
                last_t = cur_time
                connected = True
            except:
                print "Could not send data to robot"
                connected = False

        # Show the image.
        cv.imshow(WINDOW_NAME, bg)

        # Capture a keypress.
        key = cv.waitKey(10) & 255

        # Escape key.
        if key == 27:
            break
        # W key: Increment exposure.
        elif key == ord('w'):
            exposure += 1
        # S key: Decrement exposure.
        elif key == ord('s'):
            exposure -= 1
        # D key: Increment threshold.
        elif key == ord('d'):
            max_color_distance += 1
        # A key: Decrement threshold.
        elif key == ord('a'):
            max_color_distance -= 1

        # Enforce bounds.
        if exposure < -7:
            exposure = -7
        elif exposure > -1:
            exposure = -1

        # 180/255/255 are the max range of the OpenCV representation of HSV.
        if max_color_distance > (180 + 255 + 255):
            max_color_distance = (180 + 255 + 255)
        elif max_color_distance < 1:
            max_color_distance = 1

        if exposure != last_exposure:
            print "Changing exposure to %d" % exposure
            capture.set(15,exposure)
        if max_color_distance != last_max_color_distance:
            print "Changing threshold to %d" % max_color_distance

        last_exposure = exposure
        last_max_color_distance = max_color_distance

    s.close()

if __name__ == '__main__':
    main()
