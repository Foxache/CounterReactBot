import os
import sys
import json
import time
import queue
import threading
from flask import Flask, request
from pynput.keyboard import Key, Controller

# --- Logger class ---
class Logger:
    def __init__(self, logfile):
        self.terminal = sys.stdout
        self.log = open(logfile, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# --- Setup ---
script_directory = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(script_directory, "console_log.txt")
sys.stdout = Logger(log_path)
sys.stderr = sys.stdout

round_data_path = os.path.join(script_directory, "round_data.json")
with open(round_data_path, "w", encoding="utf-8") as f:
    json.dump({}, f)

# --- Debug mode ---
enable_debug = input("\nEnable debug mode? (y/n): ").strip().lower() == 'y'
if enable_debug:
    print("[DEBUG] Debug mode enabled")

# --- Features toggle ---
features = {
    2: {"name": "Assist effects", "enabled": True},
    4: {"name": "Death effects", "enabled": True},
    8: {"name": "Kill effects", "enabled": True},
}

def display_menu():
    os.system("cls" if os.name == "nt" else "clear")
    print("Toggle features by typing numbers (e.g. '2 4'). Press Enter to finish:\n")
    for num, feature in features.items():
        status = "ON" if feature["enabled"] else "OFF"
        print(f"{num}. {feature['name']} [{status}]")

while True:
    display_menu()
    selection = input("\nToggle: ").strip()
    if selection == "":
        break
    for num_str in selection.split():
        try:
            num = int(num_str)
            if num in features:
                features[num]["enabled"] = not features[num]["enabled"]
        except ValueError:
            pass

# --- Config ---
CONFIG_FILE = os.path.join(script_directory, "config.txt")
HOST_STEAM_ID = ""
with open(CONFIG_FILE, "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("HOST_STEAM_ID"):
            parts = line.split("=")
            if len(parts) == 2:
                HOST_STEAM_ID = parts[1].strip().strip('"')
            break

if not enable_debug:
    if HOST_STEAM_ID == "" or HOST_STEAM_ID == "76561199128394910":
        print("[DEBUG] SteamID64 not set. Please read readme.txt")
        while True:
            time.sleep(1)
else:
    print("[DEBUG] SteamID was skipped!")
    time.sleep(1)

# --- Variables ---
keyboard = Controller()
event_queue = queue.Queue()
app = Flask(__name__)

previous_kills = 0
previous_assists = 0
previous_deaths = 0
previous_health = 100
previous_round = 0
kill_flag = False
assist_flag = False
lobotomy_flag = False
dead = False
current_round = 0

# --- Game event handler ---
@app.route("/", methods=["POST"])
def game_event():
    global previous_kills, previous_assists, previous_deaths, previous_health, previous_round
    global kill_flag, assist_flag, lobotomy_flag, dead, current_round

    data = request.json
    map_data = data.get("map", {})
    if isinstance(map_data, dict):
        current_round = map_data.get("round", 0)
        if current_round == 0:
            previous_kills = 0
            previous_assists = 0
            previous_deaths = 0
            previous_health = 100
            previous_round = 0
            kill_flag = False
            assist_flag = False
            lobotomy_flag = False
            print("[DEBUG] Reset tracking variables")

    player = data.get("player", {})
    if player.get("steamid") == HOST_STEAM_ID:
        health = player.get("state", {}).get("health", 100)
        dead = health == 0

        current_kills = player.get("match_stats", {}).get("kills", previous_kills)
        current_deaths = player.get("match_stats", {}).get("deaths", previous_deaths)
        current_assists = player.get("match_stats", {}).get("assists", previous_assists)

        if features[4]["enabled"] and current_deaths > previous_deaths and not lobotomy_flag:
            keyboard.press(Key.f7)
            keyboard.release(Key.f7)
            lobotomy_flag = True
        else:
            lobotomy_flag = False
        previous_deaths = current_deaths

        if features[8]["enabled"] and not kill_flag:
            if current_kills > previous_kills and current_kills - previous_kills == 1:
                keyboard.press(Key.f7)
                keyboard.release(Key.f7)
                kill_flag = True
        else:
            kill_flag = False
        previous_kills = current_kills

        if features[2]["enabled"] and not assist_flag:
            if current_assists > previous_assists and current_assists - previous_assists == 1:
                keyboard.press(Key.f7)
                keyboard.release(Key.f7)
                assist_flag = True
        if current_round != previous_round:
            assist_flag = False
        previous_assists = current_assists

        previous_round = current_round

    return "", 200

# --- Process queue loop ---
def process_queue_loop():
    while True:
        while not event_queue.empty():
            try:
                event_queue.get_nowait()()
            except queue.Empty:
                break
        time.sleep(0.01)

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=process_queue_loop, daemon=True).start()
    threading.Thread(target=app.run, kwargs={"host": "127.0.0.1", "port": 5000}, daemon=True).start()
    print("[MAIN] Running... press Ctrl+C to quit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[MAIN] Exiting")
