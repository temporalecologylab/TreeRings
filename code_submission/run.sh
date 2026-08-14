#!/bin/bash
#docker run -u=$(id -u $USER):$(id -g $USER) -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix:rw --network=host -v $(pwd)/app:/app --rm camera_action


jetson-containers run --privileged  -v $(pwd)/app:/home $(autotag opencv) 