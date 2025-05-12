#!/bin/bash
# Grant 777 permissions to /dev/ttyUSB0
sudo chmod 777 /dev/ttyUSB0

# Run the default command passed to the container
exec "$@"
bash
