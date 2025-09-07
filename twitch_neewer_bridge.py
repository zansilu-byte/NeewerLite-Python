#!/usr/bin/python3

import asyncio
import aiohttp
from twitchio.ext import commands

print("Script starting...")

# REQUIRED: Your Twitch bot's OAuth Access Token.
# This is NOT your stream key. See the updated instructions on how to get this.
TWITCH_ACCESS_TOKEN = "hn94iyt53u89obj3rovmovmn931z2p"
# REQUIRED: Your Twitch channel name.
TWITCH_CHANNEL = "zansilu"
# REQUIRED: Your Twitch bot's Client ID. Register an application at https://dev.twitch.tv/console/apps
TWITCH_CLIENT_ID = "81a6tav8mxgoajx24887uaj3iiu3io"
# REQUIRED: Your Twitch bot's Client Secret. Keep this secure!
TWITCH_CLIENT_SECRET = "jhercav9i9cf2amgon48fjy2wj621v"
# REQUIRED: The User ID of your Twitch bot account.
TWITCH_BOT_ID = "36265090"


NEEWER_API_URL = "http://localhost:8080/NeewerLite-Python/doAction"

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
        print("Checking for Neewer HTTP server...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{NEEWER_API_URL}?list") as response:
                    if response.status == 200:
                        print("Neewer HTTP server is running.")
                    else:
                        print(f"Error connecting to Neewer HTTP server: {response.status}")
        except aiohttp.ClientConnectorError:
            print("Could not connect to the Neewer HTTP server. Make sure the NeewerLite-Python.py script is running with the --http argument.")

    @commands.command()
    async def light(self, ctx: commands.Context, *args):
        if not args:
            await ctx.send("You need to specify a command for the light. Available commands: on, off, color, brightness, temp, scene")
            return

        command = args[0].lower()

        # The twitch_neewer_bridge.py script should rely on the NeewerLite-Python.py HTTP server
        # for light discovery and control, not directly run NeewerLite-Python.py as a subprocess.
        # Assuming LIGHT_MAC_ADDRESS is configured by the user.

        if command == "on":
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&on")
            await ctx.send(f'Turning the light on.')
        elif command == "off":
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&off")
            await ctx.send(f'Turning the light off.')
        elif command == "color":
            if len(args) < 2:
                await ctx.send("You need to specify a color.")
                return
            color = args[1].lower()
            hue = self.get_hue_for_color(color)
            if hue is None:
                await ctx.send(f"Invalid color: {color}")
                return
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&mode=hsi&hue={hue}&sat=100&bri=100")
            await ctx.send(f'Setting the light color to {color}.')
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
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&mode=cct&bri={brightness}")
            await ctx.send(f'Setting the light brightness to {brightness}.')
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
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&mode=cct&temp={temp}")
            await ctx.send(f'Setting the color temperature to {temp}.')
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
            await self.send_neewer_command(f"light={LIGHT_MAC_ADDRESS}&mode=anm&scene={scene}")
            await ctx.send(f'Setting the scene to {scene}.')
        else:
            await ctx.send(f"Invalid light command: {command}")
            return

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