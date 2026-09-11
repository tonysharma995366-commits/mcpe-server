import os
import sys
import time
import json
import zipfile
import subprocess
import requests

BOT_TOKEN = "8972471605:AAE7hhT8QO5N_hnfHTIX1PxRzmkRBm5voyY"
CHAT_ID = "8972471605"
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
            
    send_message("World extract karke server me set ki ja rahi hai...")
    stop_server()
    world_folder_name = os.path.splitext(file_name)[0].replace(" ", "_")
    target_extract = os.path.join(WORLDS_DIR, world_folder_name)
    os.makedirs(target_extract, exist_ok=True)
    
    with zipfile.ZipFile(local_zip, 'r') as zip_ref:
        zip_ref.extractall(target_extract)
        
    update_property("level-name", world_folder_name)
    start_server()
    send_message(f"World successfully import ho gayi!\nLevel Name: {world_folder_name}\nServer restarted.")

def handle_updates():
    offset = 0
    send_message("Minecraft Server Bot Ready!\nCommands:\n/status\n/backup\n/seed <seed>\n/restart\n/stopserver\n/startserver\n\nDirect world .zip file bhej kar restore kar sakte hain.")
    
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
                    
                if text == "/status":
                    out = run_cmd("screen -ls").stdout
                    status = "ONLINE" if "mcpe" in out else "OFFLINE"
                    playit = "ONLINE" if "playit-tunnel" in out else "OFFLINE"
                    send_message(f"Server Status:\nMinecraft: {status}\nPlayit: {playit}")
                    
                elif text == "/backup":
                    send_message("Backup zip create ho raha hai...")
                    backup_zip = os.path.join(BASE_DIR, "world_backup.zip")
                    if os.path.exists(backup_zip):
                        os.remove(backup_zip)
                    run_cmd(f"cd {BASE_DIR} && zip -r {backup_zip} worlds/ server.properties")
                    send_document(backup_zip, "Minecraft Server World Backup")
                    
                elif text.startswith("/seed"):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send_message("Seed specify karein! Example: /seed 987654321")
                    else:
                        seed_val = parts[1].strip()
                        new_world = f"world_{int(time.time())}"
                        send_message(f"Seed: {seed_val} apply karke naya world banaya ja raha hai...")
                        stop_server()
                        update_property("level-seed", seed_val)
                        update_property("level-name", new_world)
                        start_server()
                        send_message("Naya world generate ho gaya!")
                        
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
