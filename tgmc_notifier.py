# Settings
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
SERVER_IP = "YOUR_SERVER_IP/DOMEN"
SERVER_PORT = 25565

# Telegram bot initialization
bot = Bot(token=BOT_TOKEN)

# Variables
message_id = None  # ID of the current message
server_was_offline = True
last_status = {}  # Last server status
offline_time = None

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


async def get_server_status():
    """Retrieve the current status of the Minecraft server."""
    try:
        server = JavaServer.lookup(f"{SERVER_IP}:{SERVER_PORT}")
        status = server.status()
        return {
            "online": True,
            "players": status.players.online,
            "player_names": [player.name for player in (status.players.sample or [])],
        }
    except Exception as e:
        logging.error(f"Error checking server status: {e}")
        return {"online": False, "players": 0, "player_names": []}


async def send_message(text):
    """Send a message to Telegram and save its ID."""
    global message_id
    try:
        message = await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
        message_id = message.message_id
        logging.info("New message created in Telegram.")
    except TelegramError as e:
        logging.error(f"Error sending message: {e}")


async def update_message(text):
    """Update the text of an existing message."""
    global message_id
    if message_id is None:
        await send_message(text)  # If no message exists, create a new one
    else:
        try:
            await bot.edit_message_text(chat_id=CHAT_ID, message_id=message_id, text=text, parse_mode="Markdown")
            logging.info("Message in Telegram updated.")
        except TelegramError as e:
            if "message is not modified" in str(e):
                logging.info("Message text unchanged, update skipped.")
            else:
                logging.error(f"Error updating message: {e}")


async def delete_all_messages():
    """Delete the current message if it exists."""
    global message_id
    if message_id is not None:
        try:
            await bot.delete_message(chat_id=CHAT_ID, message_id=message_id)
            logging.info(f"Message with ID {message_id} deleted.")
            message_id = None
        except TelegramError as e:
            logging.error(f"Error deleting message: {e}")


async def periodic_check():
    """Periodically check the server status."""
    global server_was_offline, last_status, offline_time, message_id

    while True:
        status = await get_server_status()

        if status["online"]:
            if server_was_offline:  # Server just came online
                # Delete old messages
                await delete_all_messages()

                # Create a new message with server info
                text = (
                    f"🟢 **Server is online**\n"
                    f"👥 Players online: {status['players']}\n"
                    f"{', '.join(status['player_names']) if status['player_names'] else 'Empty'}"
                )
                await send_message(text)
                last_status = status  # Update the last status
                server_was_offline = False
                offline_time = None  # Reset offline timer
            elif status != last_status:  # If the status changed (players or list)
                text = (
                    f"🟢 **Server is online**\n"
                    f"👥 Players online: {status['players']}\n"
                    f"{', '.join(status['player_names']) if status['player_names'] else 'Empty'}"
                )
                await update_message(text)
                last_status = status  # Update the last status
        else:
            text = "🔴 **Server is offline**"
            if not server_was_offline:  # Server just went offline
                offline_time = asyncio.get_event_loop().time()
                await update_message(text)  # Update the message
                server_was_offline = True
            elif offline_time and (asyncio.get_event_loop().time() - offline_time > 600):
                # Delete the message if the server is offline for more than 10 minutes
                await delete_all_messages()
                offline_time = None  # Reset the timer

        await asyncio.sleep(20)  # Check interval


if __name__ == "__main__":
    try:
        asyncio.run(periodic_check())
    except KeyboardInterrupt:
        logging.info("Bot stopped.")
