#!/usr/bin/env python

import time
import os
import sys
import logging
import json

import bottle
import gevent
import geventwebsocket
from bottle import post, get
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError

# try/except removed here on purpose so folks can see why things break
import config

logging.basicConfig(level=config.log_level, format=config.log_format)
log = logging.getLogger("kiln-controller")
log.info("Starting kiln controller")

script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, script_dir + '/lib/')
profile_path = config.kiln_profiles_directory

from oven import SimulatedOven, RealOven, Profile
from ovenWatcher import OvenWatcher, WebSocketObserver  

app = bottle.Bottle()

if config.simulate == True:
    log.info("this is a simulation")
    oven = SimulatedOven()
else:
    log.info("this is a real kiln")
    oven = RealOven()
ovenWatcher = OvenWatcher(oven)
# this ovenwatcher is used in the oven class for restarts
oven.set_ovenwatcher(ovenWatcher)


@app.route('/')
def index():
    return bottle.redirect('/picoreflow/index.html')

@app.route('/state')
def state():
    return bottle.redirect('/picoreflow/state.html')

@app.get('/api/stats')
def handle_api():
    log.info("/api/stats command received")
    if hasattr(oven,'pid'):
        if hasattr(oven.pid,'pidstats'):
            return json.dumps(oven.pid.pidstats)


@app.post('/api')
def handle_api_post(): # Renamed function for clarity
    """Handles commands received via HTTP POST requests."""
    try:
        command = bottle.request.json
        # Basic validation of the incoming request body
        if not command or not isinstance(command, dict) or 'cmd' not in command:
            log.warning(f"/api POST received invalid data: {command}")
            return bottle.HTTPResponse(status=400, body=json.dumps({"success": False, "error": "Invalid command format"}))

        cmd = command['cmd']
        log.info(f"/api POST received cmd: {cmd}")

        success = True # Assume success unless an action function returns False or raises Error
        error_msg = None
        action_result = None # Store result from perform functions if needed

        # --- Use Action Functions ---
        if cmd == 'run':
            wanted_profile_name = command.get('profile') # Changed variable name
            # perform_start_profile expects profile NAME
            if not wanted_profile_name:
                success, error_msg = False, "Profile name missing"
            else:
                try:
                    # Call the action function
                    success = perform_start_profile(wanted_profile_name)
                    if not success and oven.state != "IDLE":
                        # Provide specific feedback if start failed due to wrong state
                        error_msg = "Oven not IDLE"
                except ValueError as e:
                    # Catch profile not found error from perform_start_profile
                     success, error_msg = False, str(e)
                except Exception as e:
                    # Catch other unexpected errors during start
                    log.error(f"Unexpected error during API start profile: {e}", exc_info=True)
                    success, error_msg = False, "Internal error during start"

        elif cmd == 'pause':
            success = perform_pause_kiln()
            if not success: error_msg = "Oven not RUNNING"

        elif cmd == 'resume':
            success = perform_resume_kiln()
            if not success: error_msg = "Oven not PAUSED"

        elif cmd == 'stop':
            success = perform_stop_kiln()
            # Stop is usually considered successful even if already stopped

        elif cmd == 'memo':
            # Memo command doesn't change state, just logs
            log.info(f"API memo: {command.get('memo','')}")
            success = True # Memo is always successful

        elif cmd == 'stats':
             # Handle stats request within POST API if needed, though GET is more typical
             if hasattr(oven,'pid') and hasattr(oven.pid,'pidstats'):
                 return json.dumps(oven.pid.pidstats) # Return stats directly
             else:
                 return json.dumps({}) # Return empty if no stats
        else:
            # Command not recognized
            success, error_msg = False, f"Unknown command: {cmd}"
        # --- End Use Action Functions ---

        # --- Construct and Send Response ---
        response_body = {"success": success}
        if error_msg:
            response_body["error"] = error_msg
        # Set content type header for JSON response
        bottle.response.content_type = 'application/json'
        # Return appropriate HTTP status code based on success
        status_code = 200 if success else 400 # 400 Bad Request for failed actions
        return bottle.HTTPResponse(status=status_code, body=json.dumps(response_body))
        # --- End Construct and Send Response ---

    except json.JSONDecodeError:
        log.warning("/api POST received non-JSON body.")
        return bottle.HTTPResponse(status=400, body=json.dumps({"success": False, "error": "Request body must be valid JSON"}))
    except Exception as e:
        # Catch unexpected errors during request handling
        log.error(f"Error handling /api POST request: {e}", exc_info=True)
        return bottle.HTTPResponse(status=500, body=json.dumps({"success": False, "error": "Internal server error"}))


def find_profile(wanted):
    '''
    given a wanted profile name, find it and return the parsed
    json profile object or None.
    '''
    #load all profiles from disk
    profiles = get_profiles()
    json_profiles = json.loads(profiles)

    # find the wanted profile
    for profile in json_profiles:
        if profile['name'] == wanted:
            return profile
    return None

@app.route('/picoreflow/:filename#.*#')
def send_static(filename):
    log.debug("serving %s" % filename)
    return bottle.static_file(filename, root=os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "public"))


def get_websocket_from_request():
    env = bottle.request.environ
    wsock = env.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')
    return wsock


@app.route('/control')
def handle_control():
    """Handles commands (RUN, STOP, PAUSE, RESUME) received via WebSocket."""
    wsock = get_websocket_from_request()
    client_addr = wsock.environ.get('REMOTE_ADDR', 'Unknown') # Get client address for logging
    log.info(f"WebSocket (control) opened for: {client_addr}")

    while True:
        try:
            message = wsock.receive() # Blocks until message received or socket closes

            if message is None: # Check for client disconnect
                log.info(f"WebSocket (control) client disconnected: {client_addr}")
                break

            log.info(f"WS Received (control) from {client_addr}: {message}")

            try:
                msgdict = json.loads(message)
                cmd = msgdict.get("cmd")

                # --- Use Action Functions ---
                if cmd == "RUN":
                    # perform_start_profile expects profile NAME, not object
                    profile_name = msgdict.get('profile', {}).get('name') # Safely get name
                    if profile_name:
                        try:
                            success = perform_start_profile(profile_name)
                            if not success: log.warning(f"WS RUN: Failed to start profile '{profile_name}' (check oven state).")
                        except ValueError as e: # Catch profile not found specifically
                            log.error(f"WS RUN failed: {e}")
                            # Optionally send error back to client
                            wsock.send(json.dumps({"success": False, "error": str(e)}))
                        except Exception as e: # Catch other unexpected errors during start
                            log.error(f"WS RUN unexpected error: {e}", exc_info=True)
                    else:
                        log.warning("WS RUN command received but missing profile name.")

                elif cmd == "STOP":
                    perform_stop_kiln()

                elif cmd == "PAUSE":
                    perform_pause_kiln()

                elif cmd == "RESUME":
                    perform_resume_kiln()
                # --- End Use Action Functions ---
                else:
                    log.warning(f"Unknown WS control command received: {cmd}")
            except json.JSONDecodeError:
                 log.warning("WS Received non-JSON message on control socket.")
            except Exception as e:
                 # Catch errors from processing the command *after* receiving message
                 log.error(f"Error processing WS control command: {e}", exc_info=True)
        except WebSocketError:
            # Expected error when client disconnects
            log.info(f"WebSocket (control) closed (WebSocketError) for: {client_addr}")
            break
        except Exception as e:
            # Catch unexpected errors during receive or loop
            log.error(f"Unexpected error in control websocket loop for {client_addr}: {e}", exc_info=True)
            break # Exit loop on error
    log.info(f"WebSocket (control) connection handling finished for: {client_addr}")


@app.route('/storage')
def handle_storage():
    wsock = get_websocket_from_request()
    log.info("websocket (storage) opened")
    while True:
        try:
            message = wsock.receive()
            if not message:
                break
            log.debug("websocket (storage) received: %s" % message)

            try:
                msgdict = json.loads(message)
            except:
                msgdict = {}

            if message == "GET":
                log.info("GET command received")
                wsock.send(get_profiles())
            elif msgdict.get("cmd") == "DELETE":
                log.info("DELETE command received")
                profile_obj = msgdict.get('profile')
                if delete_profile(profile_obj):
                  msgdict["resp"] = "OK"
                wsock.send(json.dumps(msgdict))
                #wsock.send(get_profiles())
            elif msgdict.get("cmd") == "PUT":
                log.info("PUT command received")
                profile_obj = msgdict.get('profile')
                #force = msgdict.get('force', False)
                force = True
                if profile_obj:
                    #del msgdict["cmd"]
                    if save_profile(profile_obj, force):
                        msgdict["resp"] = "OK"
                    else:
                        msgdict["resp"] = "FAIL"
                    log.debug("websocket (storage) sent: %s" % message)

                    wsock.send(json.dumps(msgdict))
                    wsock.send(get_profiles())
            time.sleep(1) 
        except WebSocketError:
            break
    log.info("websocket (storage) closed")


@app.route('/config')
def handle_config():
    wsock = get_websocket_from_request()
    log.info("websocket (config) opened")
    while True:
        try:
            message = wsock.receive()
            wsock.send(get_config())
        except WebSocketError:
            break
        time.sleep(1)
    log.info("websocket (config) closed")


@app.route('/status')
def handle_status():
    wsock = get_websocket_from_request()
    observer = WebSocketObserver(wsock)
    ovenWatcher.add_observer(observer)
    log.info("websocket (status) opened")
    while True:
        try:
            message = wsock.receive()
            wsock.send("Your message was: %r" % message)
        except WebSocketError:
            break
        time.sleep(1)
    log.info("websocket (status) closed")


# --- Action functions used to control the kiln ---

def perform_start_profile(profile_identifier):
    """
    Starts the oven run using the specified profile identifier, which can be
    either the profile's internal 'name' field or its filename.

    Args:
        profile_identifier (str): The internal name or filename of the profile.

    Returns:
        bool: True if start was successful, False otherwise.

    Raises:
        ValueError: If the oven state is not IDLE or profile format is invalid.
        FileNotFoundError: If identified as a filename but file not found.
    """
    log.info(f"Action: Start Profile identified by '{profile_identifier}'")
    if oven.state != "IDLE":
        log.warning(f"Cannot start profile, oven is not IDLE (State: {oven.state}).")
        return False

    if not profile_identifier or not isinstance(profile_identifier, str):
         log.error("Cannot start profile, invalid identifier provided.")
         raise ValueError("Invalid profile identifier provided for start.")

    profile_obj = None
    profile_source_info = "" # For logging

    # --- Determine if identifier is filename or internal name ---
    if profile_identifier.lower().endswith('.json'):
        # Assume it's a filename
        profile_source_info = f"file '{profile_identifier}'"
        profile_path_dir = getattr(config, 'kiln_profiles_directory', os.path.join(script_dir, "storage", "profiles"))
        profile_filepath = os.path.join(profile_path_dir, profile_identifier)

        if not os.path.exists(profile_filepath):
            log.error(f"Cannot start profile, file not found: {profile_filepath}")
            raise FileNotFoundError(f"Profile file '{profile_identifier}' not found.")
        try:
            with open(profile_filepath, 'r', encoding='utf-8') as f:
                profile_obj = json.load(f) # Load the profile object directly
        except json.JSONDecodeError as e:
            log.error(f"Error decoding JSON from profile file {profile_identifier}: {e}")
            raise ValueError(f"JSON error in profile '{profile_identifier}'.")
        except Exception as e:
            log.error(f"Unexpected error loading profile file {profile_identifier}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load profile file '{profile_identifier}'.") from e
    else:
        # Assume it's an internal profile name, use find_profile helper
        profile_source_info = f"internal name '{profile_identifier}'"
        profile_obj = find_profile(profile_identifier)
        if profile_obj is None:
            log.error(f"Cannot start profile, profile with name '{profile_identifier}' not found.")
            # Use ValueError consistent with previous internal name search failure
            raise ValueError(f"Profile '{profile_identifier}' not found.")
    # --- End identifier check ---

    # --- Proceed if profile object was loaded/found ---
    if profile_obj:
        try:
            # Basic validation
            if not (profile_obj.get("type") == "profile" and isinstance(profile_obj.get("data"), list)):
                 log.error(f"Invalid profile format loaded from {profile_source_info}")
                 raise ValueError(f"Invalid profile format in '{profile_identifier}'.")

            # Start the run
            profile = Profile(json.dumps(profile_obj))
            oven.run_profile(profile, startat=0, allow_seek=config.seek_start)
            ovenWatcher.record(profile)
            log.info(f"Profile from {profile_source_info} (Loaded Name: '{profile_obj.get('name', 'N/A')}') successfully started.")
            return True

        except Exception as e: # Catch errors during Profile creation or run_profile
             log.error(f"Unexpected error starting profile from {profile_source_info}: {e}", exc_info=True)
             raise RuntimeError(f"Failed to start profile '{profile_identifier}'.") from e
    else:
        # This case should technically be handled above, but as a fallback:
        log.error(f"Failed to obtain profile object for identifier '{profile_identifier}'.")
        return False # Should not be reached if errors are raised correctly


def perform_pause_kiln():
    """Sets the oven state to PAUSED if currently RUNNING."""
    log.info("Action: Pause Kiln")
    if oven.state == "RUNNING":
        oven.state = 'PAUSED' # Direct state change
        log.info("Kiln Paused.")
        # State change notification handled by OvenWatcher
        return True
    else:
        log.warning(f"Cannot pause, kiln state is not RUNNING (State: {oven.state})")
        return False

def perform_resume_kiln():
    """Sets the oven state to RUNNING if currently PAUSED."""
    log.info("Action: Resume Kiln")
    if oven.state == "PAUSED":
        oven.state = 'RUNNING' # Direct state change
        log.info("Kiln Resumed.")
        # State change notification handled by OvenWatcher
        return True
    else:
        log.warning(f"Cannot resume, kiln state is not PAUSED (State: {oven.state})")
        return False

def perform_stop_kiln():
    """Stops the kiln (aborts current run) if running or paused."""
    log.info("Action: Stop Kiln")
    if oven.state in ["RUNNING", "PAUSED"]:
        oven.abort_run() # Use the existing abort method
        log.info("Kiln Stopped (run aborted).")
        # State change notification handled by OvenWatcher
        return True
    else:
        log.info(f"Kiln already stopped (State: {oven.state}).")
        return True # Stop considered successful if already stopped

# --- End Action Functions ---



def get_profiles():
    try:
        profile_files = os.listdir(profile_path)
    except:
        profile_files = []
    profiles = []
    for filename in profile_files:
        with open(os.path.join(profile_path, filename), 'r') as f:
            profiles.append(json.load(f))
    profiles = normalize_temp_units(profiles)
    return json.dumps(profiles)


def save_profile(profile, force=False):
    profile=add_temp_units(profile)
    profile_json = json.dumps(profile)
    filename = profile['name']+".json"
    filepath = os.path.join(profile_path, filename)
    if not force and os.path.exists(filepath):
        log.error("Could not write, %s already exists" % filepath)
        return False
    with open(filepath, 'w+') as f:
        f.write(profile_json)
        f.close()
    log.info("Wrote %s" % filepath)
    return True

def add_temp_units(profile):
    """
    always store the temperature in degrees c
    this way folks can share profiles
    """
    if "temp_units" in profile:
        return profile
    profile['temp_units']="c"
    if config.temp_scale=="c":
        return profile
    if config.temp_scale=="f":
        profile=convert_to_c(profile);
        return profile

def convert_to_c(profile):
    newdata=[]
    for (secs,temp) in profile["data"]:
        temp = (5/9)*(temp-32)
        newdata.append((secs,temp))
    profile["data"]=newdata
    return profile

def convert_to_f(profile):
    newdata=[]
    for (secs,temp) in profile["data"]:
        temp = ((9/5)*temp)+32
        newdata.append((secs,temp))
    profile["data"]=newdata
    return profile

def normalize_temp_units(profiles):
    normalized = []
    for profile in profiles:
        if "temp_units" in profile:
            if config.temp_scale == "f" and profile["temp_units"] == "c": 
                profile = convert_to_f(profile)
                profile["temp_units"] = "f"
        normalized.append(profile)
    return normalized

def delete_profile(profile):
    profile_json = json.dumps(profile)
    filename = profile['name']+".json"
    filepath = os.path.join(profile_path, filename)
    os.remove(filepath)
    log.info("Deleted %s" % filepath)
    return True

def get_config():
    return json.dumps({"temp_scale": config.temp_scale,
        "time_scale_slope": config.time_scale_slope,
        "time_scale_profile": config.time_scale_profile,
        "kwh_rate": config.kwh_rate,
        "currency_type": config.currency_type})    



#-------------------------------------------

# --- Display UI Imports (Using new paths) ---
try:
    from display_ui.display_screen import KilnDisplay
    from display_ui.menu_ui import MenuUI
    from display_ui.rotary_input import RotaryInput
    # We also need RPi.GPIO for cleanup, import conditionally
    if config.enable_rotary_input:
        try:
            import RPi.GPIO as GPIO
        except (ImportError, RuntimeError):
            log.warning("RPi.GPIO not found/loadable, cleanup will be skipped.")
            GPIO = None
    else:
        GPIO = None
except ImportError as e:
    log.error(f"Failed to import display_ui modules: {e}", exc_info=True)
    # Decide if UI is critical
    log.warning("Display UI failed to import, proceeding without it.")
    # sys.exit(1) # Uncomment to make UI mandatory
    KilnDisplay = None # Define as None to allow checks later
    MenuUI = None
    RotaryInput = None
# --- End Display UI Imports ---


# -------------------------------------------
# Display UI Initialization & Integration
# -------------------------------------------
display = None
ui = None
rotary_thread = None

# Only initialize if the necessary classes were imported successfully
if KilnDisplay and MenuUI and RotaryInput:
    try:
        log.info("Initializing Display UI components...")

        # 1) Initialize the display
        display_config = getattr(config, 'DISPLAY_CONFIG', {})
        display = KilnDisplay.get_instance(display_config)
        if not display or not display.device: # Check if hardware init succeeded
            raise RuntimeError("KilnDisplay failed to initialize device.")
        log.info("KilnDisplay initialized.")

        # 2) Create the MenuUI, pass oven object, and register as observer
        action_callbacks = {
            'start' : perform_start_profile,
            'pause' : perform_pause_kiln,    
            'stop'  : perform_stop_kiln,     
            'resume': perform_resume_kiln 
        }
        ui = MenuUI(display, action_callbacks=action_callbacks)
        ovenWatcher.add_observer(ui) 
        log.info("MenuUI initialized and attached as observer.")

        # 3) Initialize and Start rotary input thread (if enabled in config)
        if config.enable_rotary_input:
            rotary_thread = RotaryInput(ui) # RotaryInput handles internal checks
            rotary_thread.start()
            # Log hardware availability status based on RotaryInput's check
            if rotary_thread.available:
                log.info("RotaryInput thread started (Hardware Available).")
            else:
                log.warning("RotaryInput thread started but hardware check failed.")
        else:
            log.info("Rotary input disabled by config, thread not started.")

    except Exception as e:
        log.error(f"Error during Display UI initialization: {e}", exc_info=True)
        log.warning("Continuing without Display UI...")
        # Ensure objects are None if init failed partially
        display = None
        ui = None
        rotary_thread = None
else:
    # This logs if the initial imports at the top of the file failed
    log.warning("Display UI classes not imported, skipping UI initialization.")
# -------------------------------------------


# --- Other Observer Initialization (e.g., Telegram) ---
from lib.telegram_observer import TelegramObserver # Keep this import here

if config.enable_telegram_observer:
    try:
        telegram_observer = TelegramObserver()
        ovenWatcher.add_observer(telegram_observer)
        log.info("Telegram observer added.")
    except Exception as e:
        log.error(f"Failed to initialize Telegram observer: {e}")
# --- End Observer Initialization ---




def main():
    ip = "0.0.0.0"
    port = config.listening_port
    log.info("listening on %s:%d" % (ip, port))

    server = WSGIServer((ip, port), app,
                        handler_class=WebSocketHandler)
    try:
        # This line blocks until the server is stopped (e.g., by Ctrl+C)
        server.serve_forever()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        log.info("KeyboardInterrupt received, shutting down.")
    except Exception as e:
        # Log any other unexpected errors during server operation
        log.error(f"Server error: {e}", exc_info=True)
    finally:
        # --- ADDED CLEANUP BLOCK ---
        log.info("Performing final cleanup...")
        server.stop() # Stop the web server

        # Stop rotary input thread gracefully
        if rotary_thread and rotary_thread.is_alive():
            log.info("Stopping RotaryInput thread...")
            if hasattr(rotary_thread, 'stop'):
                rotary_thread.stop() # Signal the thread to stop
            rotary_thread.join(timeout=1) # Wait briefly for it to exit
            if rotary_thread.is_alive():
                 log.warning("RotaryInput thread did not exit cleanly.")

        # Clean up GPIO (only if RPi.GPIO was successfully imported)
        # Use the GPIO variable defined near the UI imports
        if GPIO and hasattr(GPIO, 'cleanup'):
            try:
                GPIO.cleanup()
                log.info("GPIO cleanup done.")
            except Exception as e:
                log.error(f"GPIO cleanup error: {e}")
        elif config.enable_rotary_input: # Log only if it was supposed to be enabled
             log.warning("GPIO cleanup skipped (RPi.GPIO module not available/imported).")

        # Clean up display (if possible and cleanup method exists)
        # Check if display and display.device exist and device has cleanup
        if display and hasattr(display, 'device') and display.device and hasattr(display.device, 'cleanup'):
             try:
                 display.device.cleanup()
                 log.info("Display device cleanup done.")
             except Exception as e:
                 log.error(f"Display cleanup error: {e}")

        log.info("Shutdown complete.")
        # --- END ADDED CLEANUP BLOCK ---


if __name__ == "__main__":
    main()
