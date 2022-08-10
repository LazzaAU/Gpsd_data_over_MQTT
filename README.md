Gpsd data over MQTT

This purpose of this code is to send GPSD data from one Raspberry PI (RPI) and send it to Home Assistant on another RPI via MQTT.


## Hardware Setup ##

1. 2 Raspberry pi's, one with Home Assistant running on it, second one has the GPS receiver attached
2. GPS receiver
3. On the RPI with the gps receiver attached, install gpsd and gpsdclient

## Functionailty ##

This code will listen for events from a GPSD client (in my case a USB GPS receiver plugged into a RPI 3b+)
It will then send the latitude and longitude coordinates along with some other gps data to 
Home Assistant via MQTT which in my case is on a seperate RPI 4.

This code triggers from a Cron task and records a successful outcome or a failure in a file called /home/pi/crontasks.log
Use the command "cat /home/pi/crontasks.log" to view the contents of the log file once up and running or use
 "journalctl" command to view errors. The log file has a configurable size limit to it (default 50mb). Once the limit is reached the log is deleted and a new file is created. 
 
## Software setup ##

- Download the gpsdata.py file from this repository
- Place it on the RPI that has the GPS reciever attached. Recommend in /home/pi directory for simplicity
- Install gpsd and gpsdclient on the RPI
 ```
 sudo apt-get update
 ```
 ```
 sudo apt install gpsd
 ```
 ```
 sudo apt install gpsdclient
 ```
 
 - Open the gpsdata.py file
```
nano /home/pi/gpsdata.py
```
- Line 18 says "configure these". so in the block of code below that add your MQTT broker address, username/password if required and port. NOTE: if you dont use mqtt username and passsword the comment both thos lines with a # in the front of them.
- Change or leave caravan_gps_receiver as the value for "deviceName" to suit your needs. but remeber what you used for later. 

**TIP** - Throughout the code, Lines starting with # are comments to assist working out what the relevant code does.

**TIP #2**: 
Print messages in this code won't display during a cron task. To see print messages run this file manually from the command
 line. EG: `python3 gpsdata.py`

## Home Assistant set up in configuration.yaml ##
- Add the below to your configuration.yaml (home assistant versions 2022.6.9 ? and upwards )

mqtt:
  device_tracker:
    - name: "Caravan GPS receiver"
      state_topic: "homeassistant/caravan_gps_receiver/state"
      json_attributes_topic: "homeassistant/caravan_gps_receiver/attributes"
      json_attributes_template: "{{ value_json | tojson}}"

**NOTE** - Obviously change caravan_gps_receiver to the same topic name you choose whenadding a name for "deviceName" in the code".  
- restart HA after editing the file

## Home Assistant Automation ##
Create a automation that triggers from a MQTT topic of "homeassistant/`your_device_name`/attributes". Once triggered use the set.location service
 as the action, as per below example.

 ```
 - id: 1a06fb2f81d949c8ad6c1ff95b4d4d7c
  alias: Update Home Location
  trigger:
  - platform: mqtt
    topic: homeassistant/caravan_gps_receiver/attributes
  condition: []
  action:
  - service: homeassistant.set_location
    data_template:
      latitude: '{{ states.device_tracker.caravan_gps_receiver.attributes.latitude }}'
      longitude: '{{ states.device_tracker.caravan_gps_receiver.attributes.longitude
        }}'
```

## Create the Cron task ##

In the terminal of the RPI with the receiver attached. type ```crontab -e``` and push enter.
at the end of the file that opens add...

```*/1 * * * * /usr/bin/python3 /home/pi/gpsdata.py```

then save the file and the cron task will run. (in this case every minute). However, you can change it to every 15 minutes or what ever suits you.

`for example` 

by changing */1 in the above line to */15 or read the crontab file to see what to change for various days months, hours etc

Hope that helps 
Enjoy
