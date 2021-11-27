# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import math
import configparser
import json
import datetime
import pandas as pd
from pandas.plotting import table as tableTool
import plotly.graph_objects as go

from discord.ext import tasks, commands
from dislash import slash_commands
from dislash.interactions import *
from loguru import logger

from SeedStorage import DiscordBotToken
from Common import *
from UtilBot import *
import Commands
from Slash import *
import DB

# Event Listeners

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(prefix + 'qr to get QR code!'))
    print('\nWe are logged in as {0.user}'.format(client))

    await DB.createMainTables()

    for guild in client.guilds:
        found = False
        for emoji in guild.emojis:
            if emoji.name == "slp":
                found = True
                slpEmojiID[guild.id] = emoji.id
        if found == False:
            slpEmojiID[guild.id] = None


@client.event
# Listen for an incomming message
async def on_message(message):
    global forceAlert
    global alertPing

    # check if the message fits our prefix
    if not message.content.startswith(prefix):
        return

    # set important IDs
    discordId = message.author.id
    channelId = message.channel.id
    guildId = None
    if message.guild == None:
        # command was DMed to the bot
        guildId = None
    else:
        # command was in a server channel
        guildId = message.guild.id

    # If the author is the robot itself, then do nothing!
    if message.author == client.user:
        return

    isManager = False
    managerIds = await DB.getAllManagerIDs()
    logger.info("Manager IDs")
    logger.info(managerIds)
    if int(discordId) in managerIds:
        isManager = True

    args = message.content.split(" ")

    # If the user requests a QR code
    if message.content == prefix + "qr":
        await Commands.qrCommand(message, isManager, discordId, guildId)
        return   
    
    # user requests daily progress
    elif args[0] == prefix + "daily":
        await Commands.dailyCommand(message, args, isManager, discordId, guildId)
        return

    # user requests recent battles
    elif args[0] == prefix + "battles":
        await message.reply("Sorry, following the latest Axie Infinity update battle logs are no longer available. :(")
        #await Commands.battlesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests axie data
    elif args[0] == prefix + "axies":
        await Commands.axiesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar summary data, can be restricted to manager only via the comment
    elif args[0] == prefix + "summary":  # and isManager:
        await Commands.summaryCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar top10 data, can be restricted to manager only via the comment
    elif args[0] == prefix + "top":  # and isManager:
        await Commands.topCommand(message, args, isManager, discordId, guildId)
        return

    # user requests alerts, must be manager
    elif args[0] == prefix + "alert" and isManager:
        await Commands.alertsCommand(message, args)
        return
    
    # get export csv of scholars
    elif args[0] == prefix + "export" and isManager:
        await Commands.exportCommand(message, isManager)
        return

    elif args[0] == prefix + "getProperty":
        await Commands.getPropertyCommand(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "setProperty" and isManager:
        await Commands.setPropertyCommand(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "getScholar":
        await Commands.getScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "addScholar" and isManager:
        await Commands.addScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "removeScholar" and isManager:
        await Commands.removeScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "updateScholarShare" and isManager:
        if guildId is None:
            await message.reply(content="Please do not use payout commands in DMs with the bot, so records are available in the Discord server.")
            return
        await Commands.updateScholarShare(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "setPayoutAddress":
        if guildId is None:
            await message.reply(content="Please do not use payout commands in DMs with the bot, so records are available in the Discord server.")
            return
        await Commands.updateScholarAddress(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "addManager" and isManager:
        await Commands.addManager(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "removeManager" and isManager:
        await Commands.removeManager(message, args, isManager, discordId, guildId)
        return
    
    elif args[0] == prefix + "membership":
        await Commands.membershipCommand(message, args, isManager, discordId, guildId)
        return
     
    elif args[0] == prefix + "payout":
        if guildId is None:
            await message.reply(content="Please do not use payout commands in DMs with the bot, so records are available in the Discord server.")
            return
        await Commands.payoutCommand(message, args, isManager, discordId, guildId)
        return
    
    elif args[0] == prefix + "massPayout" and isManager:
        if guildId is None:
            await message.reply(content="Please do not use payout commands in DMs with the bot, so records are available in the Discord server.")
            return
        await Commands.payoutAllScholars(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "exportRole" and isManager:
        guild = message.guild

        # Check for role name parameter
        roleName = None
        if len(args) > 0:
            roleName = ''
            for arg in args[1:]:
                roleName += arg + " "
            roleName = roleName[:-1]
        else:
            await message.reply("Provide a role name")
            return

        # Search server for role
        roleObj = None
        for r in guild.roles:
            if r.name.startswith(roleName):
                roleObj = r
                break

        # Role not found
        if roleObj is None:
            await message.reply(f"Role matching {roleName} was not found")

        # Construct table of members with the role
        df = pd.DataFrame(columns=["Discord_ID", "Discord_Name", "Role"])
        for member in roleObj.members:
            df.loc[len(df.index)] = [member.id, member.name + '#' + member.discriminator, roleObj.name]

        # Produce CSV for the member list
        fName = roleObj.name + "_export.csv"
        df.to_csv(fName, index=False)

        # Send the CSV and clean up
        await message.reply(content=f"Member export for {roleObj.name} role, {len(roleObj.members)} members", file=discord.File(fName))
        os.remove(fName)

        return

    # user asked for command help
    elif message.content == prefix + "help":
        await helpCommand(message, discordId)
        return

    logger.warning('Unknown command entered: {}'.format(message.content))
    return


# Cron Jobs

# task to send alerts at scheduled intervals regarding scholar progress
@tasks.loop(seconds=60.0)
async def checkEnergyQuest():
    await client.wait_until_ready()

    try:
        rn = datetime.datetime.now(datetime.timezone.utc)

        # check if it's time to run a task
        if rn.hour == 18 and rn.minute == 52:  # allow 7pm EST / 11pm UTC
            # energy / quest alerts
            await nearResetAlerts(rn)

        if leaderboardPeriod < 25 and rn.hour % leaderboardPeriod == 0 and rn.minute == 0:  # allow periodically
            logger.info("Processing scheduled leaderboard posting")

            channel = client.get_channel(leaderboardChannelId);
            
            # fetch the data
            sort = "mmr"
            ascText = "desc"
            table, cacheExp = await getScholarSummary(sort, False)

            # error
            if table is None or cacheExp is None:
                logger.error("Failed to build scheduled leaderboard post")
            
            else:
                # send results
                msg = 'Hello ' + programName + ', here is the scholar summary sorted by `' + sort + " " + ascText + "`:"

                fig = go.Figure(data=[go.Table(
                    columnwidth = [75,400,100,200,150,200,150,150,150,150,100,200],
                    header=dict(values=list(table.columns),
                        fill_color="paleturquoise",
                        align='center'),
                    cells=dict(values=table.T.values,
                        fill_color='lavender',
                        align='center'))
                ])
                fig.update_layout(margin=dict(
                    l=0, #left margin
                    r=0, #right margin
                    b=0, #bottom margin
                    t=0  #top margin
                ))
                fName = 'images/summary' + str(int(time.time())) + '.png'
                fig.write_image(fName, width=1200, height=20*len(table)+30)

                await channel.send(content=msg,file=discord.File(fName))

                os.remove(fName)
            pass

    except Exception as e:
        logger.error("Error in checkEnergyQuest")
        logger.error(e)
        #traceback.print_exc()

        await sendErrorToManagers(e, "cron job")
    
    pass


# Run tasks
checkEnergyQuest.start()

# Run the client
client.run(DiscordBotToken)

