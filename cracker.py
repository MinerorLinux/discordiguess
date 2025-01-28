import sys
import hikari
import lightbulb
from collections import defaultdict, deque
import datetime
import os
import logging
import json
from dotenv import load_dotenv
from typing import DefaultDict, Deque
from PIL import Image, ImageDraw, ImageFont
import io

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No bot token provided. Set the BOT_TOKEN environment variable.")

bot = lightbulb.BotApp(token=BOT_TOKEN, prefix='.', intents=hikari.Intents.ALL)

# Create a folder for storing JSON files
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# File paths for JSON files
MOD_LOGS_FILE = os.path.join(DATA_FOLDER, "mod_logs.json")
RECENT_ACTIONS_FILE = os.path.join(DATA_FOLDER, "recent_actions.json")
USER_TIMEZONES_FILE = os.path.join(DATA_FOLDER, "user_timezones.json")
BYPASS_USERS_FILE = os.path.join(DATA_FOLDER, "bypass_users.json")

# Load data from JSON files
def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return default

mod_logs = load_json(MOD_LOGS_FILE, defaultdict(list))
support_chat_status = defaultdict(lambda: True)  # Initialize with True to allow chat by default
recent_actions = load_json(RECENT_ACTIONS_FILE, defaultdict(lambda: defaultdict(deque)))
user_timezones = load_json(USER_TIMEZONES_FILE, defaultdict(lambda: 'UTC'))
bypass_users = set(load_json(BYPASS_USERS_FILE, []))

# Save data to JSON files
def save_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, default=str, indent=4)

SUPPORT_SERVER_ID = 1094926261459111936
SUPPORT_INVITE_LINK = "https://discord.gg/uNwvyTCeJv"
STATUS_VOICE_CHANNEL_ID = 1333341675573219328  # voice channel ID

@bot.listen(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    logging.info('Bot has started!')
    try:
        # Update voice channel name to indicate the bot is online
        channel = await bot.rest.fetch_channel(STATUS_VOICE_CHANNEL_ID)
        await bot.rest.edit_channel(channel, name="🟢 Bot Status: Online")
    except Exception as e:
        logging.error(f"Error updating status channel: {e}")

@bot.listen(hikari.StoppedEvent)
async def on_stopped(event: hikari.StoppedEvent) -> None:
    logging.info('Bot has stopped!')
    try:
        # Update voice channel name to indicate the bot is offline
        if bot.rest.is_alive:
            channel = await bot.rest.fetch_channel(STATUS_VOICE_CHANNEL_ID)
            await bot.rest.edit_channel(channel, name="🔴 Bot Status: Offline")
    except Exception as e:
        logging.error(f"Error updating status channel: {e}")

@bot.command
@lightbulb.command('restart', 'Restarts the bot.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def restart(ctx: lightbulb.Context) -> None:
    try:
        await ctx.respond("Restarting the bot...")
        logging.info('Bot is restarting...')
        # Update voice channel name to indicate the bot is restarting
        channel = await bot.rest.fetch_channel(STATUS_VOICE_CHANNEL_ID)
        await bot.rest.edit_channel(channel, name="🟡 Bot Status: Restarting")
        await bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await ctx.respond("An error occurred while processing your request.")
        logging.error(f"Error in restart command: {e}")

@bot.listen(lightbulb.CommandErrorEvent)
async def on_command_error(event: lightbulb.CommandErrorEvent) -> None:
    if isinstance(event.exception, lightbulb.CommandInvocationError):
        await event.context.respond("An error occurred while executing the command.")
    elif isinstance(event.exception, lightbulb.NotOwner):
        await event.context.respond("You do not have permission to use this command.")
    elif isinstance(event.exception, lightbulb.CommandNotFound):
        await event.context.respond("Command not found.")
    else:
        await event.context.respond("An unexpected error occurred.")
    logging.error(f"Error in command {event.context.command.name}: {event.exception}")

@bot.command
@lightbulb.command('info', 'Provides information about the bot.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def info(ctx: lightbulb.Context) -> None:
    try:
        embed = hikari.Embed(
            title="Bot Information",
            description="This is a sample bot created using Hikari and Lightbulb.",
            color=hikari.Color(0xFFD700)
        )
        embed.add_field(name="Author", value="fentbusgaming", inline=True)
        embed.add_field(name="Version", value="1.2.3-233", inline=True)
        await ctx.respond(embed=embed)
    except Exception as e:
        await ctx.respond("An error occurred while processing your request.")
        logging.error(f"Error in info command: {e}")

@bot.command
@lightbulb.command('commands', 'Lists all available commands.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def commands(ctx: lightbulb.Context) -> None:
    try:
        embed = hikari.Embed(
            title="Commands",
            description="List of available commands:",
            color=hikari.Color(0xFF4500)
        )
        embed.add_field(name="/info", value="Provides information about the bot.", inline=False)
        embed.add_field(name="/commands", value="Lists all available commands.", inline=False)
        embed.add_field(name="/ban", value="Bans a user from the server.", inline=False)
        embed.add_field(name="/mute", value="Mutes a user in the server.", inline=False)
        embed.add_field(name="/kick", value="Kicks a user from the server.", inline=False)
        embed.add_field(name="/warn", value="Warns a user.", inline=False)
        embed.add_field(name="/modlogs", value="Displays moderation logs.", inline=False)
        embed.add_field(name="/settimezone", value="Sets your timezone.", inline=False)
        embed.add_field(name="/time", value="Displays the current time in your timezone.", inline=False)
        embed.add_field(name="/restart", value="Restarts the bot.", inline=False)
        embed.add_field(name="/bypass", value="Manages anti-nuke bypass list.", inline=False)
        embed.add_field(name="/support", value="Provides the support server invite link.", inline=False)
        await ctx.respond(embed=embed)
    except Exception as e:
        await ctx.respond("An error occurred while processing your request.")
        logging.error(f"Error in commands command: {e}")

@bot.command
@lightbulb.command('support', 'Provides the support server invite link.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def support(ctx: lightbulb.Context) -> None:
    try:
        await ctx.respond(f"Join our support server: {SUPPORT_INVITE_LINK}")
    except Exception as e:
        await ctx.respond("An error occurred while processing your request.")
        logging.error(f"Error in support command: {e}")

@bot.command
@lightbulb.option("user", "The user to add or remove from the bypass list.", hikari.User)
@lightbulb.option("action", "Add or remove the user from the bypass list.", choices=["add", "remove"])
@lightbulb.command('bypass', 'Manages the anti-nuke bypass list.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def bypass(ctx: lightbulb.Context) -> None:
    if not ctx.author.id == ctx.get_guild().owner_id:
        await ctx.respond("You do not have permission to use this command.")
        return
    user = ctx.options.user
    action = ctx.options.action
    if action == "add":
        bypass_users.add(user.id)
        await ctx.respond(f"{user.username} has been added to the bypass list.")
    elif action == "remove":
        bypass_users.discard(user.id)
        await ctx.respond(f"{user.username} has been removed from the bypass list.")
    save_json(BYPASS_USERS_FILE, list(bypass_users))

@bot.command
@lightbulb.option("text_color", "The color of the text in hex format (e.g., #FFFFFF for white).", str, required=False, default="#FFFFFF")
@lightbulb.option("bg_color", "The background color of the image in hex format (e.g., #000000 for black).", str, required=False, default="#000000")
@lightbulb.option("text", "The text to display on the image.", str, required=True)
@lightbulb.command('generateimage', 'Generates an image with specified text and colors.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def generateimage(ctx: lightbulb.Context) -> None:
    try:
        text = ctx.options.text
        bg_color = ctx.options.bg_color
        text_color = ctx.options.text_color

        # Create an image with Pillow
        img = Image.new('RGB', (400, 200), color=bg_color)
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        d.text((10, 10), text, font=font, fill=text_color)

        # Save the image to a file
        img_path = "output.png"
        img.save(img_path)

        # Send the image to the user
        await ctx.respond("Here is your generated image:", attachment=img_path)
    except Exception as e:
        await ctx.respond("An error occurred while generating the image.")
        logging.error(f"Error in generateimage command: {e}")

@bot.command
@lightbulb.option("image", "Upload an image to create a GIF.", hikari.Attachment, required=True)
@lightbulb.command('gif', 'Creates a GIF from an uploaded image.')
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def gif(ctx: lightbulb.Context) -> None:
    try:
        image = ctx.options.image
        img_data = await image.read()
        img = Image.open(io.BytesIO(img_data))

        # Create a GIF with a single frame
        gif_path = "output.gif"
        img.save(gif_path, save_all=True, append_images=[img], loop=0, duration=500)

        await ctx.respond("Here is your GIF:", attachment=gif_path)
    except Exception as e:
        await ctx.respond("An error occurred while creating the GIF.")
        logging.error(f"Error in gif command: {e}")

@bot.listen(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    try:
        if event.is_bot or not event.guild_id or event.author_id in bypass_users:
            return
        if event.guild_id == SUPPORT_SERVER_ID and not support_chat_status[event.guild_id]:
            await event.message.delete()
            return
        if "discord.gg/" in event.content:
            await event.message.delete()
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Invite links are not allowed in this server.",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append(f"Deleted invite link from {event.author.username}")
            save_json(MOD_LOGS_FILE, mod_logs)
    except Exception as e:
        logging.error(f"Error in on_message_create event: {e}")

@bot.listen(hikari.GuildMessageDeleteEvent)
async def on_message_delete(event: hikari.GuildMessageDeleteEvent) -> None:
    try:
        if event.is_bot or not event.guild_id:
            return
        recent_actions[event.guild_id]['message_deletes'].append(datetime.datetime.now())
        if len(recent_actions[event.guild_id]['message_deletes']) > 5:
            recent_actions[event.guild_id]['message_deletes'].popleft()
        if len(recent_actions[event.guild_id]['message_deletes']) == 5 and (
                datetime.datetime.now() - recent_actions[event.guild_id]['message_deletes'][0]).total_seconds() < 10:
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Mass message deletion detected!",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append("Mass message deletion detected!")
            save_json(MOD_LOGS_FILE, mod_logs)
            save_json(RECENT_ACTIONS_FILE, recent_actions)
    except Exception as e:
        logging.error(f"Error in on_message_delete event: {e}")

@bot.listen(hikari.GuildChannelCreateEvent)
async def on_channel_create(event: hikari.GuildChannelCreateEvent) -> None:
    try:
        if event.is_bot or not event.guild_id:
            return
        recent_actions[event.guild_id]['channel_creates'].append(datetime.datetime.now())
        if len(recent_actions[event.guild_id]['channel_creates']) > 5:
            recent_actions[event.guild_id]['channel_creates'].popleft()
        if len(recent_actions[event.guild_id]['channel_creates']) == 5 and (
                datetime.datetime.now() - recent_actions[event.guild_id]['channel_creates'][0]).total_seconds() < 10:
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Mass channel creation detected!",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append("Mass channel creation detected!")
            save_json(MOD_LOGS_FILE, mod_logs)
            save_json(RECENT_ACTIONS_FILE, recent_actions)
    except Exception as e:
        logging.error(f"Error in on_channel_create event: {e}")

@bot.listen(hikari.RoleCreateEvent)
async def on_role_create(event: hikari.RoleCreateEvent) -> None:
    try:
        if event.is_bot or not event.guild_id:
            return
        recent_actions[event.guild_id]['role_creates'].append(datetime.datetime.now())
        if len(recent_actions[event.guild_id]['role_creates']) > 5:
            recent_actions[event.guild_id]['role_creates'].popleft()
        if len(recent_actions[event.guild_id]['role_creates']) == 5 and (
                datetime.datetime.now() - recent_actions[event.guild_id]['role_creates'][0]).total_seconds() < 10:
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Mass role creation detected!",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append("Mass role creation detected!")
            save_json(MOD_LOGS_FILE, mod_logs)
            save_json(RECENT_ACTIONS_FILE, recent_actions)
    except Exception as e:
        logging.error(f"Error in on_role_create event: {e}")

@bot.listen(hikari.RoleDeleteEvent)
async def on_role_delete(event: hikari.RoleDeleteEvent) -> None:
    try:
        if event.is_bot or not event.guild_id:
            return
        recent_actions[event.guild_id]['role_deletes'].append(datetime.datetime.now())
        if len(recent_actions[event.guild_id]['role_deletes']) > 5:
            recent_actions[event.guild_id]['role_deletes'].popleft()
        if len(recent_actions[event.guild_id]['role_deletes']) == 5 and (
                datetime.datetime.now() - recent_actions[event.guild_id]['role_deletes'][0]).total_seconds() < 10:
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Mass role deletion detected!",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append("Mass role deletion detected!")
            save_json(MOD_LOGS_FILE, mod_logs)
            save_json(RECENT_ACTIONS_FILE, recent_actions)
    except Exception as e:
        logging.error(f"Error in on_role_delete event: {e}")

@bot.listen(hikari.MemberDeleteEvent)
async def on_member_delete(event: hikari.MemberDeleteEvent) -> None:
    try:
        if event.is_bot or not event.guild_id:
            return
        recent_actions[event.guild_id]['member_bans'].append(datetime.datetime.now())
        if len(recent_actions[event.guild_id]['member_bans']) > 5:
            recent_actions[event.guild_id]['member_bans'].popleft()
        if len(recent_actions[event.guild_id]['member_bans']) == 5 and (
                datetime.datetime.now() - recent_actions[event.guild_id]['member_bans'][0]).total_seconds() < 10:
            embed = hikari.Embed(
                title="Anti-Nuke",
                description="Mass member ban detected!",
                color=hikari.Color(0xFF0000)
            )
            await event.get_channel().send(embed=embed)
            mod_logs[event.guild_id].append("Mass member ban detected!")
            save_json(MOD_LOGS_FILE, mod_logs)
            save_json(RECENT_ACTIONS_FILE, recent_actions)
    except Exception as e:
        logging.error(f"Error in on_member_delete event: {e}")

bot.run()  # Run the bot with the provided token and prefix