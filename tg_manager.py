import os
import sys
import time
import json
import zipfile
import subprocess
import requests

BOT_TOKEN = "8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID = "6955911349"
BASE_DIR = "/root/mcpe-server"
PROPERTIES_FILE = os.path.join(BASE_DIR, "server.properties")
WORLDS_DIR = os.path.join(BASE_DIR, "worlds")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def send_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as doc:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": doc}, timeout=60)
    except Exception as e:
        send_message(f"Backup send error: {e}")

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def send_to_console(mc_cmd):
    cmd = f'screen -S mcpe -X stuff "{mc_cmd}^M"'
    run_cmd(cmd)

def stop_server():
    run_cmd("screen -S mcpe -X quit")
    time.sleep(2)

def start_server():
    stop_server()
    cmd = f'screen -dmS mcpe bash -c "cd {BASE_DIR} && LD_LIBRARY_PATH=. ./bedrock_server"'
    run_cmd(cmd)
    time.sleep(2)

def update_property(key, value):
    if not os.path.exists(PROPERTIES_FILE):
        return
    with open(PROPERTIES_FILE, "r") as f:
        lines = f.readlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    with open(PROPERTIES_FILE, "w") as f:
        f.writelines(new_lines)

def handle_document(doc):
    file_name = doc.get("file_name", "world.zip")
    if not file_name.endswith((".zip", ".mcworld")):
        send_message("Kripya sirf .zip ya .mcworld format ki file bhejein!")
        return
    file_id = doc["file_id"]
    send_message("World zip download ho rahi hai...")
    res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
    file_path = res["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    
    local_zip = os.path.join(BASE_DIR, "uploaded_world.zip")
    r = requests.get(download_url, stream=True)
    with open(local_zip, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    send_message("World extract ho rahi hai...")
    stop_server()
    world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
    target_extract = os.path.join(WORLDS_DIR, world_folder_name)
    os.makedirs(target_extract, exist_ok=True)
    
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(target_extract)
        
    update_property("level-name", world_folder_name)
    start_server()
    send_message(f"World successfully import ho gayi!\nLevel Name: {world_folder_name}\nServer restarted.")

HELP_TEXT = """Minecraft Server Control Panel

Server & Power:
/status - Server & Tunnel check
/startserver - Start server
/stopserver - Stop server
/restart - Restart server
/logs - Recent console logs

World & Backup:
/backup - Download world .zip
/seed <number> - Generate world with seed
[Send .zip file] - Auto upload & apply world

Player Management:
/players - View online players
/op <player> - Give OP / Admin
/deop <player> - Remove OP / Admin
/kick <player> - Kick player
/ban <player> - Ban player
/unban <player> - Unban player

Game Rules & Gameplay:
/coords - Turn ON coordinates
/keepinventory - Toggle KeepInventory on death
/pvp <on|off> - Turn PVP ON/OFF
/cheats <on|off> - Enable/Disable cheats
/difficulty <easy|normal|hard|peaceful>
/gamemode <survival|creative|adventure>
/time <day|night|noon|midnight>
/weather <clear|rain|thunder>

Utility:
/say <message> - Broadcast announcement to all
/cmd <command> - Run custom Minecraft command
"""

def handle_updates():
    offset = 0
    send_message("Minecraft Server Bot Ready!\nType /help sabhi commands dekhne ke liye.")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            r = requests.get(url, timeout=40)
            data = r.json()
            if not data.get("ok"):
                time.sleep(2)
                continue
                
            for item in data.get("result", []):
                offset = item["update_id"] + 1
                msg = item.get("message", {})
                chat = str(msg.get("chat", {}).get("id", ""))
                if chat != CHAT_ID:
                    continue
                    
                if "document" in msg:
                    handle_document(msg["document"])
                    continue
                    
                text = msg.get("text", "").strip()
                if not text:
                    continue
                
                # Command routing
                if text in ["/start", "/help"]:
                    send_message(HELP_TEXT)

                elif text == "/status":
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "mcpe" in out else "OFFLINE"
                    playit = "ONLINE" if "playit-tunnel" in out else "OFFLINE"
                    send_message(f"Status:\nMinecraft: {status}\nPlayit Tunnel: {playit}")

                elif text == "/players":
                    send_to_console("list")
                    time.sleep(1)
                    run_cmd("screen -S mcpe -X hardcopy /tmp/screen_log.txt")
                    try:
                        with open("/tmp/screen_log.txt", "r") as f:
                            lines = f.readlines()
                        last_lines = "".join(lines[-10:])
                        send_message(f"Player List:\n{last_lines}")
                    except Exception:
                        send_message("Command sent: list (check in-game)")

                elif text == "/logs":
                    run_cmd("screen -S mcpe -X hardcopy /tmp/screen_log.txt")
                    try:
                        with open("/tmp/screen_log.txt", "r") as f:
                            lines = f.readlines()
                        log_sample = "".join(lines[-15:])
                        send_message(f"Recent Logs:\n{log_sample}")
                    except Exception as e:
                        send_message(f"Logs nahi read ho paye: {e}")

                elif text.startswith("/op "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'op "{player}"')
                    send_message(f"OP rights given to: {player}")

                elif text.startswith("/deop "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'deop "{player}"')
                    send_message(f"OP rights removed for: {player}")

                elif text.startswith("/kick "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'kick "{player}"')
                    send_message(f"Player kicked: {player}")

                elif text.startswith("/ban "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'ban "{player}"')
                    send_message(f"Player banned: {player}")

                elif text.startswith("/unban "):
                    player = text.split(" ", 1)[1].strip()
                    send_to_console(f'unban "{player}"')
                    send_message(f"Player unbanned: {player}")

                elif text == "/coords":
                    send_to_console("gamerule showcoordinates true")
                    send_message("Coordinates turned ON!")

                elif text == "/keepinventory":
                    send_to_console("gamerule keepinventory true")
                    send_message("KeepInventory enabled (Inventory drop nahi hogi)!")

                elif text.startswith("/pvp "):
                    val = text.split(" ", 1)[1].strip().lower()
                    pvp_val = "true" if val in ["on", "true", "1"] else "false"
                    send_to_console(f"gamerule pvp {pvp_val}")
                    update_property("pvp", pvp_val)
                    send_message(f"PVP set to: {pvp_val}")

                elif text.startswith("/cheats "):
                    val = text.split(" ", 1)[1].strip().lower()
                    cheats_val = "true" if val in ["on", "true", "1"] else "false"
                    update_property("allow-cheats", cheats_val)
                    send_to_console(f"changesetting allow-cheats {cheats_val}")
                    send_message(f"Allow-cheats set to: {cheats_val}")

                elif text.startswith("/difficulty "):
                    diff = text.split(" ", 1)[1].strip().lower()
                    if diff in ["peaceful", "easy", "normal", "hard"]:
                        send_to_console(f"difficulty {diff}")
                        update_property("difficulty", diff)
                        send_message(f"Difficulty set to: {diff}")
                    else:
                        send_message("Valid options: peaceful, easy, normal, hard")

                elif text.startswith("/gamemode "):
                    gm = text.split(" ", 1)[1].strip().lower()
                    if gm in ["survival", "creative", "adventure"]:
                        send_to_console(f"defaultgamemode {gm}")
                        update_property("gamemode", gm)
                        send_message(f"Default gamemode set to: {gm}")
                    else:
                        send_message("Valid options: survival, creative, adventure")

                elif text.startswith("/time "):
                    t_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"time set {t_val}")
                    send_message(f"Time set to: {t_val}")

                elif text.startswith("/weather "):
                    w_val = text.split(" ", 1)[1].strip().lower()
                    send_to_console(f"weather {w_val}")
                    send_message(f"Weather set to: {w_val}")

                elif text.startswith("/say "):
                    msg_say = text.split(" ", 1)[1].strip()
                    send_to_console(f'say [ADMIN]: {msg_say}')
                    send_message(f"Broadcast sent: {msg_say}")

                elif text.startswith("/cmd "):
                    mc_cmd = text.split(" ", 1)[1].strip()
                    send_to_console(mc_cmd)
                    send_message(f"Executed: {mc_cmd}")

                elif text == "/backup":
                    send_message("Backup zip create ho raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties")
                    send_document(backup_zip, "Minecraft World Backup")

                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Example: /seed 987654321")
                    else:
                        seed_val = parts[1].strip()
                        new_world = f"world_{int(time.time())}"
                        send_message(f"Seed {seed_val} apply karke naya world ban raha hai...")
                        stop_server()
                        update_property("level-seed", seed_val)
                        update_property("level-name", new_world)
                        start_server()
                        send_message("Naya world active ho gaya!")

                elif text == "/restart":
                    send_message("Restarting server...")
                    start_server()
                    send_message("Server restarted.")

                elif text == "/stopserver":
                    stop_server()
                    send_message("Server stopped.")

                elif text == "/startserver":
                    start_server()
                    send_message("Server started.")

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    handle_updates()
