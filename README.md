# carla-multiplayer

Multiplayer Carla using a ghetto game-streaming concept; in summary:

- A vehicle and a sensor are created in Carla using Carla's PythonAPI
- Controls are received as JSON via UDP and applied to the vehicle (using the PythonAPI)
    - The controls are originally sourced from a PS4 or Xbox 360 controller
- Images are pulled (using the PythonAPI), converted to .webp and sent via UDP
    - The images are displayed using pyame  

So, all the work and rendering is done server-side, the client-side merely captures input and displays the sensor images.

## Install (MacOS)

- Create a virtualenv
    - ```virtualenv -p `which python3` venv ```
- Activate the virtualenv
    - `source venv/bin/activate`
- install the requirements
    - `pip install -r requirements.txt`
- Install pygame (special process for MacOS)
    - `brew install sdl sdl_image sdl_mixer sdl_ttf portmidi`
    - `pip install https://github.com/pygame/pygame/archive/master.zip`
- If you're using an Xbox 360 controller; install 360Controller/360Controller
    - https://github.com/360Controller/360Controller/releases/tag/v1.0.0-alpha.5

## Run

- Server (for a single client)
    - `python3 -m carla_multiplayer.server 13337 13338 vehicle.komatsu.830e 192.168.137.196`
        - `13337` = vehicle port
        - `13338` = screen port
        - `vehicle.komatsu.830e` = vehicle blueprint
        - `192.168.137.196` = client host
- Client (to connect to a server)
    - `python3 -m carla_multiplayer.client 192.168.137.251 13337 13338`
        - `13337` = vehicle port
        - `13338` = screen port
        - `192.168.137.251` = server host
- Coordinator (TODO)
     - Use Pyro4 to create all the required objects and instruct a Player object on what to do 

## Main components

- Server (you need one of these per Client)
    - Vehicle
        - Create a vehicle actor in Carla
        - Apply controls to that actor
    - Sensor
        - Create a sensor actor in Carla (attached to the vehicle)
        - Pull images from it
- Client (you need one per server)
    - Controller
        - Read axis and button data from a PS4 or Xbox 360 controller
        - Send controls to the Vehicle
    - Screen
        - Read images from the Sensor
        - Write them to the local display

## Supporting components

- Looper
    - Provide start/stop semantics for threading w/ before loop, before work, work, after work and after loop calls
- TimedLooper
    - Same as above but on a strict loop period
- Threader
    - Provide start/stop semantics for one or more threads
- UDP
    - Sender
        - Send datagrams with minimal waiting using queues 
    - Receiver
        - Receive datagrams and invoke callbacks with minimal waiting using queues
