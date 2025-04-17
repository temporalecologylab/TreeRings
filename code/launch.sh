#!/bin/bash

sudo docker run -it --rm --net=host --runtime nvidia -e DISPLAY=$DISPLAY --privileged -v /dev/video0:/dev/video0 -v /lib/modules:/lib/modules -v /tmp/argus_socket:/tmp/argus_socket --device /dev/video0:/dev/video0 --device /dev/ttyUSB0:/dev/ttyUSB0 -v ./:/app:rw -v /tmp/.X11-unix/:/tmp/.X11-unix tim_image

