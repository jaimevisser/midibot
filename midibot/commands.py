import logging
import os
import shutil
from typing import Union
import uuid

import discord

from midibot import Store, SongModal, Songs
from discord import Cog, Option, guild_only, slash_command
from discord.commands import default_permissions


_log = logging.getLogger(__name__)

servers = [1004388945422987304, 908282497769558036]

class Commands(Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.songs = Songs()

    async def song_search(self, ctx: discord.AutocompleteContext):
        return await self.songs.song_search(ctx.value)
    
    async def wrong_server(self, ctx) -> bool:
        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return True
        return False
    
    async def get_song(self, ctx, song_str: str) -> Union[None, dict]:
        song_obj = self.songs.get(song_str)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
        return song_obj

    @slash_command()
    async def download(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        ),
    ):
        """Download files for a song."""
        if not (song_obj := await self.get_song(ctx, song)) : return
        
        song_obj = self.songs.get_attachements(song_obj)

        (files, attachements) = song_obj

        if len(attachements) > 0:
            await ctx.respond("There you go", files=attachements, ephemeral=True)
        else:
            await ctx.respond(
                "No files attached to that song, use /upload to add them.",
                ephemeral=True,
            )

        for f in files:
            os.remove(f)

    @slash_command()
    @guild_only()
    @default_permissions(administrator=True)
    async def add(self, ctx: discord.ApplicationContext):
        """Add a new song to the database."""
        if await self.wrong_server(ctx): return

        async def add_new_song(
            interaction: discord.Interaction,
            data: dict
        ):
            data["added_by"] = ctx.author.id
            self.songs.add_song(data)

            await interaction.response.send_message("Song added", ephemeral=True)

        modal = SongModal(add_new_song, title="Add a new song")
        await ctx.send_modal(modal)

    @slash_command()
    @guild_only()
    @default_permissions(administrator=True)
    async def edit(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        ),
    ):
        """Edit an existing song."""
        if await self.wrong_server(ctx): return
        if not (song_obj := await self.get_song(ctx, song)) : return

        async def update_song(
            interaction: discord.Interaction,
            data: dict
        ):
            if self.songs.update(song_obj,data):
                await interaction.response.send_message("Song updated", ephemeral=True)
            else:
                await ctx.respond("Updating failed", ephemeral=True)

        modal = SongModal(update_song, song_obj, title="Edit song")
        await ctx.send_modal(modal)

    @slash_command()
    @guild_only()
    @default_permissions(administrator=True)
    async def upload(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        ),
        file: discord.Attachment
    ):
        """Upload files for a song."""
        if await self.wrong_server(ctx): return
        if not (song_obj := await self.get_song(ctx, song)) : return
        
        saved = await self.songs.add_attachment(song_obj, file)

        if (saved is True):
            await ctx.respond(f"File added or replaced", ephemeral=True)
        if (saved is False):
            await ctx.respond(
                "I don't know what to do with that file. Make sure it is one of the following types:\n"
                + ", ".join(Songs.file_exts),
                ephemeral=True,
            )

    @slash_command()
    @guild_only()
    @default_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        ),
    ):
        """Remove a song and all accompanying files."""
        if await self.wrong_server(ctx): return
        if not (song_obj := await self.get_song(ctx, song)) : return

        if not self.songs.remove(song_obj):
            await ctx.respond("I don't know that song?", ephemeral=True)
        else:
            await ctx.respond("Song removed", ephemeral=True)

    @slash_command()
    @guild_only()
    async def rate(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        ),
        rating: Option(int, "Rating from 0 to 5", min_value=0, max_value=5)
    ):
        """Rate a song"""
        if await self.wrong_server(ctx): return
        if not (song_obj := await self.get_song(ctx, song)) : return

        self.songs.rate(song_obj,ctx.author.id, rating)
        await ctx.respond("Your rating has been added, thanks!", ephemeral=True)


    @slash_command()
    @guild_only()
    async def list(self, ctx: discord.ApplicationContext):
        """Get a list of the top rated songs."""

        def songsorter(song: dict):
            return song.get("rating", float(0))

        sorted = self.songs.songs.data.copy()
        sorted.sort(key=songsorter, reverse=True)

        chunk_size = 30

        chunked = [sorted[i:i+chunk_size] for i in range(0, len(sorted), chunk_size)]

        for songs in chunked:
            list = ""

            for song in songs:
                list += f'{song.get("rating", float(0))} : {self.songs.song_to_string(song)}\n'

            await ctx.respond(list, ephemeral=True)



