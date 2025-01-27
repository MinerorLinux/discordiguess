import discord
from discord.ext import commands
import datetime
import json
import os
from collections import defaultdict, deque

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)

# Create a folder for storing JSON files
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# File paths for JSON files
WHITELIST_FILE = os.path.join(DATA_FOLDER, "whitelist.json")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "settings.json")

# Store whitelist and settings
class Config:
    def __init__(self):
        self.whitelist = set(self.load_json(WHITELIST_FILE, []))
        self.settings = self.load_json(SETTINGS_FILE, {
            "anti_channel_create": True,
            "anti_channel_delete": True,
            "anti_role_create": True,
            "anti_role_delete": True,
            "anti_ban": True,
            "anti_kick": True,
            "punishment": "timeout",  # can be "timeout" or "kick"
            "timeout_duration": 600,  # duration in seconds
            "anti_invite_links": True,
            "anti_mass_messages": True,
            "mass_message_threshold": 5,
            "mass_message_timeframe": 10  # seconds
        })

    def load_json(self, file_path, default):
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                return json.load(file)
        return default

    def save_json(self, file_path, data):
        with open(file_path, "w") as file:
            json.dump(data, file, default=str, indent=4)

    def save(self):
        self.save_json(WHITELIST_FILE, list(self.whitelist))
        self.save_json(SETTINGS_FILE, self.settings)


config = Config()

# Dictionary to track recent messages for anti-mass messaging
recent_messages = defaultdict(lambda: deque(maxlen=config.settings["mass_message_threshold"]))


@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')


@bot.command()
@commands.has_permissions(administrator=True)
async def whitelist(ctx, member: discord.Member):
    """Whitelist a user from anti-nuke checks"""
    config.whitelist.add(member.id)
    config.save()
    embed = discord.Embed(
        title="Whitelist",
        description=f"{member.mention} has been whitelisted.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def unwhitelist(ctx, member: discord.Member):
    """Remove a user from whitelist"""
    config.whitelist.discard(member.id)
    config.save()
    embed = discord.Embed(
        title="Unwhitelist",
        description=f"{member.mention} has been removed from the whitelist.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def viewwhitelist(ctx):
    """View the current whitelist"""
    if config.whitelist:
        members = [f"<@{member_id}>" for member_id in config.whitelist]
        embed = discord.Embed(
            title="Whitelisted Members",
            description="\n".join(members),
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="Whitelisted Members",
            description="The whitelist is currently empty.",
            color=discord.Color.blue()
        )
    embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def viewsettings(ctx):
    """View the current anti-nuke settings"""
    settings = "\n".join([f"{key}: {value}" for key, value in config.settings.items()])
    embed = discord.Embed(
        title="Current Settings",
        description=settings,
        color=discord.Color.blue()
    )
    embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)


async def handle_punishment(guild: discord.Guild, member: discord.Member):
    if config.settings["punishment"] == "timeout":
        duration = config.settings["timeout_duration"]
        await member.timeout_for(datetime.timedelta(seconds=duration), reason="Anti-nuke: Suspicious activity")
    else:
        await guild.kick(member, reason="Anti-nuke: Suspicious activity")


@bot.event
async def on_guild_channel_create(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if entry.user.id not in config.whitelist and config.settings["anti_channel_create"]:
            await channel.delete()
            await handle_punishment(channel.guild, entry.user)


@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.user.id not in config.whitelist and config.settings["anti_channel_delete"]:
            await handle_punishment(channel.guild, entry.user)


@bot.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.user.id not in config.whitelist and config.settings["anti_role_create"]:
            await role.delete()
            await handle_punishment(role.guild, entry.user)


@bot.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if entry.user.id not in config.whitelist and config.settings["anti_role_delete"]:
            await handle_punishment(role.guild, entry.user)


@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.user.id not in config.whitelist and config.settings["anti_ban"]:
            await guild.unban(user)
            await handle_punishment(guild, entry.user)


@bot.event
async def on_member_remove(member):
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.user.id not in config.whitelist and config.settings["anti_kick"]:
            await handle_punishment(member.guild, entry.user)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Anti-invite links
    if config.settings["anti_invite_links"] and "discord.gg/" in message.content:
        await message.delete()
        embed = discord.Embed(
            title="Invite Link Detected",
            description=f"{message.author.mention}, invite links are not allowed.",
            color=discord.Color.red()
        )
        embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
        await message.channel.send(embed=embed)
        return

    # Anti-mass messages
    if config.settings["anti_mass_messages"]:
        now = datetime.datetime.now()
        recent_messages[message.author.id].append(now)

        if len(recent_messages[message.author.id]) == config.settings["mass_message_threshold"]:
            first_message_time = recent_messages[message.author.id][0]
            if (now - first_message_time).total_seconds() < config.settings["mass_message_timeframe"]:
                embed = discord.Embed(
                    title="Mass Messaging Detected",
                    description=f"{message.author.mention}, you are sending messages too quickly.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
                await message.channel.send(embed=embed)
                await handle_punishment(message.guild, message.author)
                recent_messages[message.author.id].clear()


@bot.command()
@commands.has_permissions(administrator=True)
async def antinuke(ctx, setting: str, value: str):
    """Configure anti-nuke settings"""
    setting = setting.lower()
    value = value.lower()
    
    if setting in ["channels", "roles", "bans", "kicks", "invite_links", "mass_messages"]:
        if value in ["on", "off"]:
            if setting == "channels":
                config.settings["anti_channel_create"] = config.settings["anti_channel_delete"] = (value == "on")
            elif setting == "roles":
                config.settings["anti_role_create"] = config.settings["anti_role_delete"] = (value == "on")
            elif setting == "bans":
                config.settings["anti_ban"] = (value == "on")
            elif setting == "kicks":
                config.settings["anti_kick"] = (value == "on")
            elif setting == "invite_links":
                config.settings["anti_invite_links"] = (value == "on")
            elif setting == "mass_messages":
                config.settings["anti_mass_messages"] = (value == "on")
            config.save()
            embed = discord.Embed(
                title="Anti-Nuke Setting Updated",
                description=f"Anti-{setting} has been turned {value}.",
                color=discord.Color.green()
            )
            embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
            await ctx.send(embed=embed)
    elif setting == "punishment":
        if value in ["timeout", "kick"]:
            config.settings["punishment"] = value
            config.save()
            embed = discord.Embed(
                title="Punishment Setting Updated",
                description=f"Punishment has been set to {value}.",
                color=discord.Color.green()
            )
            embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
            await ctx.send(embed=embed)
    elif setting == "timeout_duration":
        try:
            duration = int(value)
            config.settings["timeout_duration"] = duration
            config.save()
            embed = discord.Embed(
                title="Timeout Duration Updated",
                description=f"Timeout duration has been set to {duration} seconds.",
                color=discord.Color.green()
            )
            embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
            await ctx.send(embed=embed)
        except ValueError:
            embed = discord.Embed(
                title="Invalid Duration",
                description="Please provide a valid number for timeout duration.",
                color=discord.Color.red()
            )
            embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
            await ctx.send(embed=embed)


@bot.command(name="help")
async def bothelp(ctx):
    """Displays the help message"""
    embed = discord.Embed(
        title="Help",
        description="List of available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(name="!whitelist <member>", value="Whitelist a user from anti-nuke checks", inline=False)
    embed.add_field(name="!unwhitelist <member>", value="Remove a user from whitelist", inline=False)
    embed.add_field(name="!viewwhitelist", value="View the current whitelist", inline=False)
    embed.add_field(name="!viewsettings", value="View the current anti-nuke settings", inline=False)
    embed.add_field(name="!antinuke <setting> <value>", value="Configure anti-nuke settings", inline=False)
    embed.add_field(name="!help", value="Displays this help message", inline=False)
    embed.set_footer(text="AntiEverything Bot", icon_url=bot.user.avatar.url)
    await ctx.send(embed=embed)

# Replace 'YOUR_TOKEN' with your bot's token
bot.run('YOUR_TOKEN')