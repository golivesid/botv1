import time
import aria2p
import requests
import os
from pyrogram import Client, filters
from datetime import datetime

# Initialize aria2p API client
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

# Initialize the Telegram bot client
api_id = 23054736
api_hash = "d538c2e1a687d414f5c3dce7bf4a743c"
bot_token = "7107662045:AAGAekejr9l3U0vSy7ze8JEk7oo-cN9xcDw"
app = Client("Spidy", api_id, api_hash, bot_token=bot_token)

up = {}


def add_download(api, uri):
    download = api.add_uris([uri])
    return download

def get_status(api, gid):
    try:
        download = api.get_download(gid)
        total_length = download.total_length
        completed_length = download.completed_length
        download_speed = download.download_speed
        file_name = download.name
        progress = (completed_length / total_length) * 100 if total_length > 0 else 0
        is_complete = download.is_complete

        return {
            "gid": download.gid,
            "status": download.status,
            "file_name": file_name,
            "total_length": format_bytes(total_length),
            "completed_length": format_bytes(completed_length),
            "download_speed": format_bytes(download_speed),
            "progress": f"{progress:.2f}%",
            "is_complete": is_complete
        }
    except Exception as e:
        print(f"Failed to get status for GID {gid}: {e}")
        raise

async def progress(current, total, client, msg_id, file_name, chat_id):
    past_time = up[file_name]['time']
    current_time = datetime.now()
    time_difference = (current_time - past_time).total_seconds()
    speed = current - up[file_name]['current']
    up[file_name]['current'] = current

    status_text = (f"Status : Uploading\nFile Name : {file_name}\nSpeed : {format_bytes(speed / time_difference)}/s\n"
                   f"Size : {format_bytes(total)}\nProgress : {current * 100 / total:.1f}%")

    if time_difference > 3:
        up[file_name]['time'] = current_time
        await client.edit_message_text(chat_id, msg_id, status_text)

def remove_download(api, gid):
    try:
        api.remove([gid])
        print(f"Successfully removed download: {gid}")
    except Exception as e:
        print(f"Failed to remove download: {e}")
        raise

def add_both(vid, thumb):
    video = add_download(aria2, vid)
    thumbnail = add_download(aria2, thumb)
    print("Added Download:", video.gid)
    print("Added Download:", thumbnail.gid)
    return video, thumbnail

def format_bytes(byte_count):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    index = 0
    while byte_count >= 1024 and index < len(suffixes) - 1:
        byte_count /= 1024
        index += 1
    return f"{byte_count:.2f} {suffixes[index]}"

@app.on_message(filters.private & filters.text)
async def terabox(client, message):
    if message.text.startswith("https://"):
        query = message.text
        url = f"https://teraboxvideodownloader.nepcoderdevs.workers.dev/?url={query}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                resolutions = data["response"][0]["resolutions"]
                fast_download_link = resolutions["Fast Download"]
                hd_video_link = resolutions["HD Video"]
                thumbnail_url = data["response"][0]["thumbnail"]
                video_title = data["response"][0]["title"]
                reply = await message.reply_text(f"Downloading: {video_title}")
                video, thumb = add_both(fast_download_link, thumbnail_url)
                progress_bar = 0
                retry_error = 1
                while True:
                    vstatus = get_status(aria2, video.gid)
                    tstatus = get_status(aria2, thumb.gid)
                    status_text = "\n".join([f"{i} : {vstatus[i]}" for i in vstatus])
                    if progress_bar == 0:
                          pmsg = await app.send_message(chat_id=message.chat.id, text=status_text)
                          progress_bar = pmsg.id
                    else:
                        await app.edit_message_text(message.chat.id, progress_bar, status_text)
                    if vstatus['is_complete'] and tstatus['is_complete']:
                        print("Download complete!")
                        up[vstatus['file_name']] = {}
                        current_time = datetime.now()
                        up[vstatus['file_name']]['current'] = 0
                        up[vstatus['file_name']]['time'] = current_time
                        await app.send_video(chat_id=message.chat.id, video=vstatus['file_name'], thumb=tstatus['file_name'],
                                             progress=progress, progress_args=(app, progress_bar, vstatus['file_name'], message.chat.id))
                        
                        await reply.delete()
                        os.remove(vstatus['file_name'])
                        os.remove(tstatus['file_name'])
                        break
                    elif "error" in vstatus["status"].lower() or "error" in tstatus["status"].lower():
                        retry_error += 1
                        print(f"Error detected, restarting downloads, Try {retry_error}...")
                        remove_download(aria2, video.gid)
                        remove_download(aria2, thumb.gid)
                        video, thumb = add_both(fast_download_link, thumbnail_url)
                    if retry_error > 3:
                        er = await app.edit_message_text(message.chat.id, progress_bar, "Failed To Fetch the Link")
                        time.sleep(3)
                        await er.delete()
                        await reply.delete()
                        break
                    time.sleep(2)

            else:
                await app.send_message(chat_id=message.chat.id, text="Failed To Fetch the Link")
        except Exception as e:
            await app.send_message(chat_id=message.chat.id, text=str(e))
    else:
        await app.send_message(chat_id=message.chat.id, text="Send a valid URL")

print("Bot Started")
app.run()
