import os
import pyfirmata
import numpy as np
import time
import datetime
import random
import imutils
import time
import cv2

# don't forget to change the serial port to suit
board = pyfirmata.Arduino('/dev/cu.usbmodem1421')

# start an iterator thread so
# serial buffer doesn't overflow
iter8 = pyfirmata.util.Iterator(board)
iter8.start()

# set up pin D9 as Servo Output
motorPin = board.get_pin('d:3:s')
tugPin = board.get_pin('d:8:i')
motorPin.write(90)

# motion detection setup
MIN_AREA = 1000
MIN_DELTA = 100
camera = cv2.VideoCapture(0)
firstFrame = None

toyStarted = None
wiggleStarted = None
WIGGLE_DURATION = 0.2
TOY_DURATION = 10
TOY_COOLDOWN = 5
ANGLE_RANGE = 55


# video capturing setup
videoStarted = None
VIDEO_DURATION = 10
w = int(camera.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
h = int(camera.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.cv.CV_FOURCC('m', 'p', '4', 'v')
filename = None

time.sleep(2)
while True:
    now = time.time()
    (grabbed, frame) = camera.read()
    if not grabbed:
        break
    tugged = not tugPin.read()
    if tugged and not videoStarted:
        filename = 'output' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
        print "preparing to write to file " + filename
        vout = cv2.VideoWriter()
        success = vout.open(filename, fourcc, 12, (w,h), True)
        videoStarted = now
        toyStarted = now

    if videoStarted > 0:
        vout.write(frame)
        if now - videoStarted >= VIDEO_DURATION:
            print "closing video file"
            vout.release()
            videoStarted = None
            # stop the toy by settings its start to 10 seconds ago
            toyStarted = now - TOY_DURATION

            #tweet file
            # cmd = 't update "Check out my sick feline!" -f {0}'.format(filename)
            # os.system(cmd)

    # transform frame for motion detection
    smallFrame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(smallFrame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if firstFrame is None:
        firstFrame = gray
        continue

    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, MIN_DELTA, 255, cv2.THRESH_BINARY)[1]

    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # if we're not recording, start moving the toy if there's a motion contour
    if not videoStarted:
        # loop over the contours
        for c in cnts:
            # if the contour is too small, ignore it
            if cv2.contourArea(c) < MIN_AREA:
                continue        
            # if we find a contour, start moving!
            if not toyStarted:
                toyStarted = now

    if toyStarted:
        # if we haven't exceeded the toy duration, move!
        if now - toyStarted < TOY_DURATION:
            # if we're not already wiggling, start wiggling
            if not wiggleStarted or now - wiggleStarted > WIGGLE_DURATION:
                wiggleStarted = now
                angle = random.randint(90 - ANGLE_RANGE, 90 + ANGLE_RANGE)
                motorPin.write(angle)
        # if we've exceeded the duration + cooldown, reset!
        elif now - toyStarted > TOY_DURATION + TOY_COOLDOWN:
            toyStarted = None
            wiggleStarted = None

camera.relase()
cv2.destroyAllWindows()
