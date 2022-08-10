Gpsd data over MQTT

This purpose of this code is to send GPSD data from one Raspberry PI (RPI) and send it to Home Assistant on another RPI via MQTT.


## Hardware Setup ##

1. 2 Raspberry pi's, one with Home Assistant running on it, second one has the GPS receiver attached
2. GPS receiver
3. On the RPI with the gps receiver attached, install gpsd and gpsdclient

*** Functionailty ***
This code will listen for events from a GPSD client (in my case a GPS receiver plugged into raspberry pi 3b+)
It will then send the latitude and longitude coordinates along with some other gps data to 
home assistant via MQTT which is on my seperate raspberry pi 4.

This code triggers from a Cron task and records a successful outcome or a failure in a file called /home/pi/crontasks.log
Use the command "cat /home/pi/crontasks.log" to view the contents of the log file once up and running or use
 "journalctl" commnd to view errors
 
- TIPS: Read through the below code. Lines that start with "todo" indicate things you need to customise, such as add your MQTT 
ip address etc.
Lines starting with # are comments to assist working out what the relevant code does.

NOTE: 
Print messages in this code won't display during a cron task. To see print messages run this file manually from the command
 line. EG: `python3 gpsdata.py`

*** Home Assistant set up in configuration.yaml ***
mqtt:
  device_tracker:
    - name: "Caravan GPS receiver"
      state_topic: "homeassistant/caravan_gps_receiver/state"
      json_attributes_topic: "homeassistant/caravan_gps_receiver/attributes"
      json_attributes_template: "{{ value_json | tojson}}"

* NOTE - Obviously change caravan_gps_receiver to the same topic name you used in the below "configTopic" and "attrTopic". 
and restart HA after editing the file

*** Home Assistant Automation ***
Create a automation that triggers on a MQTT topic of "homeassistant/your_device_name/attributes". Once triggered use the set.location service
 as the action, as per below example.

 service: homeassistant.set_location
data_template:
  latitude: "{{ states.device_tracker.your_device_name.attributes.latitude }}"
  longitude: "{{ states.device_tracker.your_device_name.attributes.longitude }}"

*** Lastly, create the Cron task ***

In the terminal of the RPI with the receiver attached. type "crontab -e" and push enter.
at the end of the file that opens add...

*/1 * * * * /usr/bin/python3 /home/pi/gpsdata.py

then save the file and the cron task will run. (in this case every minute). However, you can change it to every 15 minutes or what ever
for example by changing 
*/1 in the above line to */15 or read the crontab file to see what to change for various days months, hours etc

Last NOTE: Log file will get deleted at 50MB and start again. That way the log file won't get infinately big 
and use up un nessasary storage space 
"""
