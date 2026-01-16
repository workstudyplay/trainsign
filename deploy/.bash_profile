source ~/rgbmatrix/bin/activate

echo "
▄▖▄▖▄▖▄▖▖ ▖▄▖▄▖▄▖▖ ▖
▐ ▙▘▌▌▐ ▛▖▌▚ ▐ ▌ ▛▖▌
▐ ▌▌▛▌▟▖▌▝▌▄▌▟▖▙▌▌▝▌.nyc

Python virtua   l environment located in /home/pi/trainsign

Run this command to activate it (run automaticly at login)
source ~/trainsign/bin/activate

the services are located in /home/pi/trainsign

Main python file for application:
/home/pi/trainsign/src/main.py
/home/pi/trainsign/src/panel.py

System service is locatated at:
/etc/systemd/system/trainsign.service

and can be controlled using the following commands:
sudo systemctl enable trainsign.service
sudo systemctl disable trainsign.service

sudo systemctl start trainsign.service
sudo systemctl stop trainsign.service
sudo systemctl restart trainsign.service
"

