import random
from typing import Optional

import discord
import pandas as pd
from discord import app_commands

from secret import TOKEN

MY_GUILD = discord.Object(id=0)


class Client(discord.Client):

    def __init__(self, intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def shuffle_member_nickname(self, member: discord.Member):
        current_nickname = member.display_name
        new_nickname = ''.join(random.sample(
            current_nickname, len(current_nickname)))
        try:
            await member.edit(nick=new_nickname)
        except discord.errors.Forbidden:
            return (False, f'Failed to change nickname of {member.display_name}')
        return (True, f'Nickname changed from {current_nickname} to {new_nickname}')

    def get_user_map(self, guild: discord.Guild):
        try:
            return pd.read_csv(f'users_map_{guild.name.replace(" ", "_").replace("/", "_")}.csv', keep_default_na=False)
        except FileNotFoundError:
            return pd.DataFrame(columns=['user_id', 'user_nickname'])


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


client = Client(intents=intents)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.tree.command(name='shuffle-nickname', description='Shuffles the nickname of the user')
@app_commands.describe(
    user='The user to shuffle the nickname of'
)
@app_commands.checks.has_any_role('Cool mods', 'nazi mods', 'Admin')
async def shuffle_nickname(interaction: discord.Interaction, user: Optional[discord.Member]):
    """Shuffles the nickname of the user or all users in the server if no user is specified"""
    if user is None:
        await interaction.response.defer()
        print(
            f'No user specified, shuffling all users in {interaction.guild.name}')
        successful_users = []
        for i, member in enumerate(interaction.guild.members):
            print(
                f'Shuffling nickname of {member.display_name}: {i}/{len(interaction.guild.members)}')
            success, response = await client.shuffle_member_nickname(member)
            if success:
                successful_users.append(member.display_name)
            print(response)
        await interaction.followup.send(f'Changed nicknames of {", ".join(successful_users)}')

    else:
        print(f'User specified: {user.display_name}')
        await interaction.response.defer()
        success, response = await client.shuffle_member_nickname(user)
        await interaction.followup.send(response)


@client.tree.command(name='backup_nicknames', description='Backs up the nicknames of all users in the server')
@app_commands.checks.has_any_role('Cool mods', 'nazi mods', 'Admin', 'Faking retardi')
async def backup_nicknames(interaction: discord.Interaction):
    """Backs up the nicknames of all users in the server"""
    print(f'Backing up nicknames of all users in {interaction.guild.name}')
    await interaction.response.defer()
    backed_up_users = []
    for member in interaction.guild.members:
        print(f'Backing up nickname of {member.display_name}')
        backed_up_users.append({'guild_id': interaction.guild.id,
                               'user_id': member.id, 'user_nickname': member.display_name})
    users_map = pd.DataFrame.from_records(backed_up_users)
    users_map.to_csv(
        f'users_map_{interaction.guild.name.replace(" ", "_").replace("/", "_")}.csv')
    await interaction.followup.send(f'Backed up nicknames of {len(users_map)} users')


@client.tree.command(name='restore_nicknames', description='Restores the nicknames of all users in the server')
@app_commands.checks.has_any_role('Cool mods', 'nazi mods', 'Admin')
async def restore_nicknames(interaction: discord.Interaction):
    """Restores the nicknames of all users in the server"""
    print(f'Restoring nicknames of all users in {interaction.guild.name}')
    await interaction.response.defer()
    users_map = client.get_user_map(interaction.guild)
    restored_users = []
    for i, member in enumerate(interaction.guild.members):
        user_nickname_match = users_map[users_map['user_id']
                                        == member.id]['user_nickname']
        user_nickname = user_nickname_match.values[0] if len(
            user_nickname_match) > 0 else None
        if user_nickname:
            print(
                f'Restoring nickname of {member.display_name}: {user_nickname}: {i}/{len(interaction.guild.members)}')
            try:
                await member.edit(nick=user_nickname)
                restored_users.append(user_nickname)
            except discord.errors.Forbidden:
                print(f'Failed to change nickname of {member.display_name}')
                continue
    await interaction.followup.send(f'Restored nicknames of {", ".join(restored_users)}')


@shuffle_nickname.error
@backup_nicknames.error
@restore_nicknames.error
async def command_error(interaction, error):
    print(error)
    if isinstance(error, app_commands.errors.MissingAnyRole):
        await interaction.response.send_message(f'You are not allowed to use this command!', ephemeral=True)
    else:
        await interaction.response.send_message(f'Error: {error}', ephemeral=True)

client.run(TOKEN)
