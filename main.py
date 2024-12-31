#Created By ShimamuX

import os
import datetime
import configparser
from tkinter import *
import customtkinter
import requests
from io import BytesIO
from PIL import Image
from tkinter import filedialog, messagebox
import yt_dlp
import pyperclip
import threading
import subprocess
import time
import webbrowser
import requests
import re
from http.cookiejar import MozillaCookieJar

_config_cache = None

def load_config():
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = configparser.ConfigParser()
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.inf")
    
    if os.path.exists(config_file_path):
        config.read(config_file_path)
        if "Settings" in config:
            url = config["Settings"].get("url", "")
            save_path = config["Settings"].get("save_path", "")
            token_file = config["Settings"].get("token_file", "")
            _config_cache = (url, save_path, token_file)
            return _config_cache
    
    _config_cache = ("", "", "") 
    return _config_cache

def save_config(url, save_path, token_file):
    config = configparser.ConfigParser()
    config["Settings"] = {
        "url": url,
        "save_path": save_path,
        "token_file": token_file,
    }
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.inf")
    with open(config_file_path, "w") as configfile:
        config.write(configfile)

def clipboard():
    clipit = pyperclip.paste()
    url_entry.delete(0, 'end')
    url_entry.insert(0, clipit)
    fetch()
    start_waiting()


def update_logs(message):
    current_time = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    logs_text.config(state="normal") 
    logs_text.insert(END, current_time + message + "\n")  
    logs_text.see(END)  
    logs_text.config(state="disabled") 

def fetch():
    global start_time, title, thumbnail_url, start_time_str
    update_logs("Fetching stream details...")
    url = url_entry.get()
    save_path = path_entry.get()
    save_config(url, save_path, token_file)
    details = get_live_stream_details(url, token_file)
    if not details:
        update_logs("Error: Unable to fetch stream details.")
        start_time = None
        title = "Error fetching details. Please check the URL."
        thumbnail_url = None
        start_time_str = "No valid start time"
        return  
    title = details["title"]
    start_time = details["start_time"]
    thumbnail_url = details["thumbnail_url"]
    localtime = time.localtime().tm_gmtoff / 3600
    if start_time:
        start_time = start_time + datetime.timedelta(hours=localtime)
    update_logs(f"Title: {title}")
    update_logs(f"Start Time: {start_time}")
    update_logs(f"Stream details Fetched")
    try:
        if thumbnail_url:
            response = requests.get(thumbnail_url, stream=True)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            image = image.crop((0, 45, 480, 315))

            photo = customtkinter.CTkImage(light_image=image, size=(256, 144))
            image_frame.configure(image=photo)
            image_frame.image = photo
    except (requests.RequestException, IOError) as e:
        print(f"Thumbnail could not be loaded, or not found")
    if start_time:
        start_time_str = "The Stream will start on:  【" + start_time.strftime("%b-%d-%Y at %I:%M:%p") + "】"
    elif title:
        start_time_str = "The Stream has been started or Ended?"
    else:
        start_time_str = "Stream Not Found or Private"
    
    Label_id8.configure(text=title)
    status_entry.delete(0, 'end')
    status_entry.insert(0, start_time_str)

def download_m3u8():
    url = url_entry.get()
    save_path = path_entry.get()
    update_logs("Looking the m3u8 file")
    try:
        ydl_opts = {'quiet': True, 'extractor-retries': 3, 'noplaylist': True, 'cookiefile': token_file}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            m3u8_url = None
            stream_info = []

            for format_info in info_dict.get('formats', []):
                if 'url' in format_info and 'm3u8' in format_info['url']:
                    m3u8_url = format_info['url']

                if 'tbr' in format_info and 'height' in format_info and 'acodec' in format_info:
                    acodec = format_info.get('acodec', ' ')
                    if acodec != 'none':
                        stream_info.append({
                            'bandwidth': int(format_info.get('tbr', 0)),
                            'resolution': f"{format_info.get('width')}x{format_info.get('height', 0)}",
                            'codecs': format_info.get('vcodec', 'unknown'),
                            'acodecs': acodec,
                            'url': format_info.get('url')
                        })

            if m3u8_url:
                m3u8_file_path = os.path.join(save_path, "video.m3u8")
                with open(m3u8_file_path, 'w') as file:
                    file.write("#EXTM3U\n")
                    file.write("#EXT-X-INDEPENDENT-SEGMENTS\n")
                    for info in stream_info:
                        file.write(f"#EXT-X-STREAM-INF:BANDWIDTH={info['bandwidth']},CODECS=\"{info['codecs']},{info['acodecs']}\",RESOLUTION={info['resolution']}\n")
                        file.write(f"{info['url']}\n")

                messagebox.showinfo("Success", f"M3U8 file saved as {m3u8_file_path}")
            else:
                messagebox.showerror("Error", "No M3U8 link found.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to download M3U8: {e}")

def start_waiting():
    url = url_entry.get()
    save_path = path_entry.get()
    update_logs("Starting to wait for the live stream...")

    if not url:
        messagebox.showerror("Error", "Please enter a video URL.")
        return
    if not save_path or not os.path.isdir(save_path):
        messagebox.showerror("Error", "Please select a valid save directory.")
        return

    def update_timer():
        if start_time is None:
            status_entry.delete(0, END)
            status_entry.insert(0, "The stream has already started or ended, Continue.")
            checkbroadcast(url, save_path)
            return 

        now = datetime.datetime.utcnow()  
        time_until_start = (start_time - now).total_seconds()

        if time_until_start <= 1:
            status_entry.delete(0, END)
            status_entry.insert(0, "Checking Broadcast...")
            checkbroadcast(url, save_path)  
        else:
            hours, remainder = divmod(time_until_start, 3600)
            minutes, seconds = divmod(remainder, 60)
            status_entry.delete(0, END)
            status_entry.insert(0, f"Waiting for live stream to start: {int(hours):02}:{int(minutes):02}:{int(seconds):02} left") 
            window.after(1000, update_timer) 
    update_timer()  

def checkbroadcast(url, save_path):
    dots = 0 

    def check_isitbroad():
        nonlocal dots
        if isitbroad(url, token_file): 
            dots = (dots + 1) % 20  
            message = "Waiting for streamer to start⦁" + "⦁" * dots
            status_entry.delete(0, END)
            status_entry.insert(0, message)
            threading.Timer(0.5, check_isitbroad).start() 
        else: 
            status_entry.delete(0, END)
            status_entry.insert(0, "Starting Recording!! (˶˃ ᵕ ˂˶) .ᐟ.ᐟ")
            print("Starting Recording...")
            start_recording(url, save_path)

    check_isitbroad()

def monitor_process(process):
    process.wait()
    if process.returncode == 0:
        update_logs("Recording completed successfully!")
    else:
        update_logs(f"Recording failed with return code {process.returncode}")

def start_recording(url, save_path):
    yt_dlp_command = f'yt-dlp -o "{save_path}/%(title)s.%(ext)s" -f bestvideo+bestaudio/best ' \
                     f'--merge-output-format mp4 --cookies {token_file} --retries 3 ' \
                     f'--socket-timeout 30 {url}'

    full_command = f'cmd.exe /c start cmd.exe /k "{yt_dlp_command}"'

    try:
        subprocess.Popen(full_command, shell=True)
        update_logs("Recording started...")
    except Exception as e:
        update_logs(f"An error occurred while starting the recording process: {e}")


def browse_save_path(entry):
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        entry.delete(0, END)
        entry.insert(0, folder_selected)
        update_logs(f"Save path selected: {folder_selected}")


token_file = None  

def token_path():
    global token_file  
    token_file = filedialog.askopenfilename(filetypes=(("Text Files", "*.txt"),))
    if token_file:
        update_logs(f"Token File selected: {token_file}")
        token_button.configure(text=os.path.basename(token_file))
    return None  

window = Tk()
window.title("EasyExtractSenchou V1.0")
window.geometry("850x360")
window.configure(bg="#360c0c")
window.iconbitmap("icon.ico")

last_url, last_save_path, token_file = load_config()

image_path = "hqdefault.png"
img = Image.open(image_path)
photo = customtkinter.CTkImage(light_image=img, size=(256, 144))
Label_id2 = customtkinter.CTkLabel(
    master=window,
    text="EasyExtractSenchou V1.0",
    font=("Arial", 24),
    text_color="#b14343",
    height=30,
    width=300,
    corner_radius=0,
    bg_color="#360c0c",
    fg_color="#360c0c",
)
Label_id2.place(x=70, y=10)
url_entry = customtkinter.CTkEntry(
    master=window,
    placeholder_text="YouTube URL",
    placeholder_text_color="#454545",
    font=("Arial", 14),
    text_color="#000000",
    height=32,
    width=370,
    border_width=2,
    corner_radius=3,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#F0F0F0",
)
url_entry.place(x=10, y=60)
url_entry.insert(0, last_url)
cli_button = customtkinter.CTkButton(
    master=window,
    text="📋",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=32,
    width=30,
    border_width=2,
    corner_radius=6,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=clipboard  
)
cli_button.place(x=385, y=60)
path_entry = customtkinter.CTkEntry(
    master=window,
    placeholder_text="Save location path",
    placeholder_text_color="#454545",
    font=("Arial", 14),
    text_color="#000000",
    height=32,
    width=300,
    border_width=2,
    corner_radius=3,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#F0F0F0",
)
path_entry.place(x=10, y=110)
path_entry.insert(0, last_save_path)
browse_button = customtkinter.CTkButton(
    master=window,
    text="Browse",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=32,
    width=95,
    border_width=2,
    corner_radius=6,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=lambda: browse_save_path(path_entry)  
)
browse_button.place(x=320, y=110)
token_button = customtkinter.CTkButton(
    master=window,
    text="Use Token",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=32,
    width=95,
    border_width=2,
    corner_radius=6,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=lambda: token_path()  
)
token_button.place(x=10, y=160)
token_button.configure(text=os.path.basename(token_file))
Button_id5 = customtkinter.CTkButton(
    master=window,
    text="Fetch",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=32,
    width=300,
    border_width=2,
    corner_radius=6,
    border_color="#962c2c",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=lambda: fetch()
)
Button_id5.place(x=120, y=160)
image_frame = customtkinter.CTkLabel(
    master=window,
    image=photo,
    text="",
    text_color="#FFFFFF",  
    corner_radius=6,  
    width=256,
    height=144,
)
image_frame.place(x=530, y=20)
Label_id8 = customtkinter.CTkLabel(
    master=window,
    text="Video Title",
    font=("Arial", 14),
    text_color="#000000",
    height=54,
    width=375,
    corner_radius=0,
    bg_color="#360c0c",
    fg_color="#ffffff",
    wraplength=375 
)
Label_id8.place(x=460, y=180)
Button_id9 = customtkinter.CTkButton(
    master=window,
    text="Extract m3u8",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=30,
    width=95,
    border_width=2,
    corner_radius=6,
    border_color="#000000",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=lambda: download_m3u8()
)
Button_id9.place(x=460, y=290)
start_button = customtkinter.CTkButton(
    master=window,
    text="Start: Waiting / Record / Download",
    font=("undefined", 14),
    text_color="#ffffff",
    hover=True,
    hover_color="#949494",
    height=30,
    width=254,
    border_width=2,
    corner_radius=6,
    border_color="#000000",
    bg_color="#360c0c",
    fg_color="#8c3636",
    command=start_waiting  
)
start_button.place(x=580, y=290)
status_entry = customtkinter.CTkEntry(
    master=window,
    placeholder_text="Stream Status",
    placeholder_text_color="#454545",
    font=("Arial", 14),
    text_color="#000000",
    height=30,
    width=374,
    border_width=2,
    corner_radius=6,
    border_color="#000000",
    bg_color="#360c0c",
    fg_color="#F0F0F0",
)
status_entry.place(x=460, y=240)
logs_text = Text(
    window,
    wrap="word",
    font=("Arial", 8),
    height=9, 
    width=68,  
    bg="#F0F0F0",  
    fg="#000000",  
    bd=2,  
    relief="solid",  
)
logs_text.place(x=10, y=200)
logs_text.config(state="disabled")
def open_donation_link(event):
    webbrowser.open("https://ko-fi.com/shimamux")
donate_label = customtkinter.CTkLabel(window, text="Click here to support me", text_color="#454545", cursor="hand2")
donate_label.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-5)
donate_label.bind("<Button-1>", open_donation_link)

def get_live_stream_details(url, cookies_file):

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"
    }
    session = requests.Session()
    cookie_jar = MozillaCookieJar()
    try:
        cookie_jar.load(cookies_file, ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return None
    
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()

        start_time_match = re.search(r'"scheduledStartTime":"(\d+)"', response.text)
        start_time = (
            datetime.datetime.utcfromtimestamp(int(start_time_match.group(1)))
            if start_time_match else None
        )
        title_match = re.search(r'"title":{"simpleText":"([^"]+)"', response.text)
        title = title_match.group(1) if title_match else None
        
        thumbnail_match = re.search(r'"thumbnail":{"thumbnails":\[{"url":"([^"]+)"', response.text)
        thumbnail_url = thumbnail_match.group(1) if thumbnail_match else None
        if thumbnail_url and thumbnail_url.startswith("//"):
            thumbnail_url = "https:" + thumbnail_url
        return {
            "start_time": start_time,
            "title": title,
            "thumbnail_url": thumbnail_url
        }
    except requests.RequestException as e:
        print(f"Error during the request: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def isitbroad(url, cookies_file):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"
    }
    session = requests.Session()
    cookie_jar = MozillaCookieJar()
    try:
        cookie_jar.load(cookies_file, ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return False
    
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status() 
        if '{"runs":[{"text":"Waiting for "}' in response.text:
            return True 
        else:
            return False  
        
    except requests.RequestException as e:
        print(f"Error during the request: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
window.mainloop()
