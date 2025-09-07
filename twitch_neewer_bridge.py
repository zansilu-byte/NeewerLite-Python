#!/usr/bin/python3

import asyncio
import aiohttp
import json # Added for parsing JSON response
from twitchio.ext import commands

print("Script starting...")

# REQUIRED: Your Twitch bot's OAuth Access Token.
# This is NOT your stream key. See the updated instructions on how to get this.
TWITCH_ACCESS_TOKEN = "YOUR_TWITCH_ACCESS_TOKEN"
# REQUIRED: Your Twitch channel name.
TWITCH_CHANNEL = "YOUR_TWITCH_CHANNEL"
# REQUIRED: Your Twitch bot's Client ID. Register an application at https://dev.twitch.tv/console/apps
TWITCH_CLIENT_ID = "YOUR_TWITCH_CLIENT_ID"
# REQUIRED: Your Twitch bot's Client Secret. Keep this secure!
TWITCH_CLIENT_SECRET = "YOUR_TWITCH_CLIENT_SECRET"
# REQUIRED: The User ID of your Twitch bot account.
TWITCH_BOT_ID = "YOUR_TWITCH_BOT_ID"

NEEWER_API_URL = "http://localhost:8080/NeewerLite-Python/doAction"

# Global variable to store discovered lights
discovered_lights = []

class Bot(commands.Bot):

    def __init__(self):
        print("Initializing bot...")
        super().__init__(token=TWITCH_ACCESS_TOKEN, prefix='!', initial_channels=[TWITCH_CHANNEL], client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET, bot_id=TWITCH_BOT_ID)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')
        await self.check_neewer_server()

    async def event_message(self, message):
        if message.echo:
            return
        print(message.content)
        await self.handle_commands(message)

    async def check_neewer_server(self):
        global discovered_lights
        print("Checking for Neewer HTTP server and discovering lights...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{NEEWER_API_URL}?list") as response:
                    if response.status == 200:
                        response_text = await response.text()
                        try:
                            # Assuming the ?list endpoint returns JSON like {"lights": ["MAC1", "MAC2"]}
                            # Or just a comma-separated string of MAC addresses.
                            # Let's assume it returns a JSON object with a "lights" key containing a list of MACs.
                            # If it's just a plain string, we'll need to adjust this.
                            data = json.loads(response_text)
                            if "lights" in data and isinstance(data["lights"], list):
                                discovered_lights = data["lights"]
                                print(f"Neewer HTTP server is running. Discovered lights: {discovered_lights}")
                            else:
                                print(f"Neewer HTTP server returned unexpected list format: {response_text}")
                                discovered_lights = [] # Clear lights if format is unexpected
                        except json.JSONDecodeError:
                            print(f"Neewer HTTP server returned non-JSON response for list: {response_text}")
                            # If it's not JSON, maybe it's a simple comma-separated list?
                            # This part might need adjustment based on actual server output.
                            discovered_lights = [mac.strip() for mac in response_text.split(',') if mac.strip()]
                            if discovered_lights:
                                print(f"Parsed lights from plain text: {discovered_lights}")
                            else:
                                print("No lights parsed from plain text response.")
                    else:
                        print(f"Error connecting to Neewer HTTP server: {response.status}")
                        discovered_lights = []
        except aiohttp.ClientConnectorError:
            print("Could not connect to the Neewer HTTP server. Make sure the NeewerLite-Python.py script is running with the --http argument.")
            discovered_lights = []

    @commands.command()
    async def light(self, ctx: commands.Context, *args):
        if not args:
            await ctx.send("You need to specify a command for the light. Available commands: on, off, color, brightness, temp, scene")
            return

        command = args[0].lower()

        if not discovered_lights:
            await ctx.send("No Neewer lights discovered. Make sure the NeewerLite-Python.py script is running with --http and lights are connected.")
            return

        for mac_address in discovered_lights: # Loop through all discovered lights
            if command == "on":
                await self.send_neewer_command(f"light={mac_address}&on")
            elif command == "off":
                await self.send_neewer_command(f"light={mac_address}&off")
            elif command == "color":
                if len(args) < 2:
                    await ctx.send("You need to specify a color.")
                    return
                color = args[1].lower()
                hue = self.get_hue_for_color(color)
                if hue is None:
                    await ctx.send(f"Invalid color: {color}")
                    return
                await self.send_neewer_command(f"light={mac_address}&mode=hsi&hue={hue}&sat=100&bri=100")
            elif command == "brightness":
                if len(args) < 2:
                    await ctx.send("You need to specify a brightness level (0-100).")
                    return
                try:
                    brightness = int(args[1])
                    if not 0 <= brightness <= 100:
                        raise ValueError
                except ValueError:
                    await ctx.send("Invalid brightness level. Please specify a number between 0 and 100.")
                    return
                await self.send_neewer_command(f"light={mac_address}&mode=cct&bri={brightness}")
            elif command == "temp":
                if len(args) < 2:
                    await ctx.send("You need to specify a color temperature (3200-5600).")
                    return
                try:
                    temp = int(args[1])
                    if not 3200 <= temp <= 5600:
                        raise ValueError
                except ValueError:
                    await ctx.send("Invalid color temperature. Please specify a number between 3200 and 5600.")
                    return
                await self.send_neewer_command(f"light={mac_address}&mode=cct&temp={temp}")
            elif command == "scene":
                if len(args) < 2:
                    await ctx.send("You need to specify a scene number (1-9).")
                    return
                try:
                    scene = int(args[1])
                    if not 1 <= scene <= 9:
                        raise ValueError
                except ValueError:
                    await ctx.send("Invalid scene number. Please specify a number between 1 and 9.")
                    return
                await self.send_neewer_command(f"light={mac_address}&mode=anm&scene={scene}")
            else:
                await ctx.send(f"Invalid light command: {command}")
                continue # Continue to next light if command is invalid for current one

        await ctx.send(f"Command '{command}' sent to all discovered lights.")


    def get_hue_for_color(self, color):
        colors = {
            "red": 0,
            "orange": 30,
            "yellow": 60,
            "green": 120,
            "cyan": 180,
            "blue": 240,
            "purple": 270,
            "magenta": 300,
        }
        return colors.get(color)

    async def send_neewer_command(self, command):
        url = f"{NEEWER_API_URL}?{command}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Error sending command to Neewer light: {response.status}")

if __name__ == "__main__":
    try:
        print("Starting bot...")
        bot = Bot()
        bot.run()
    except Exception as e:
        print(f"An error occurred: {e}")