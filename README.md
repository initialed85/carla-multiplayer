# carla-multiplayer
Multiplayer Carla using a ghetto game-streaming concept

## Install (MacOS)

- create a virtualenv
    - ```virtualenv -p `which python3` venv ```
- activate the virtualenv
    - `source venv/bin/activate`
- install the requirements
    - `pip install -r requirements.txt`
- install pygame (special process for MacOS)
    - `brew upgrade sdl sdl_image sdl_mixer sdl_ttf portmidi`
    - `pip install https://github.com/pygame/pygame/archive/master.zip`
- if you're using an Xbox 360 controller; install 360Controller/360Controller
    - https://github.com/360Controller/360Controller/releases/tag/v1.0.0-alpha.5

## Run

- test the controller
    - `python -m carla_multiplayer.controller`
    - bindings
        - left stick (left and right) = steer
        - left trigger = brake
        - right trigger = throttle
        - X (PS4) / A (Xbox 360) = hand brake
        - D pad down = select reverse gear
        - D pad up = select forward gear
