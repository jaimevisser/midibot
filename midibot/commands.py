import logging
import os
import shutil
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
        return self.songs.song_search(ctx.value)

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
        found = self.songs.get_attachements(song)

        if found == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        (files, attachements) = found

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

        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return

        async def add_new_song(
            interaction: discord.Interaction,
            artist: str,
            song: str,
            version: str,
            origin: str,
        ):
            song = {
                "artist": artist,
                "song": song,
                "version": version if version != "" else None,
                "origin": origin if origin != "" else None,
                "id": str(uuid.uuid4()),
                "type": "verified"
            }

            self.songs.songs.data.append(song)
            self.songs.sync()

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

        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return

        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        async def update_song(
            interaction: discord.Interaction,
            artist: str,
            song: str,
            version: str,
            origin: str,
        ):
            song_obj["artist"] = artist
            song_obj["song"] = song
            song_obj["version"] = version
            song_obj["origin"] = origin

            self.songs.sync()

            await interaction.response.send_message("Song updated", ephemeral=True)

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

        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return
        
        saved = self.songs.add_attachment(song, file)

        if (saved is None):
            await ctx.respond("I don't know that song?", ephemeral=True)
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

        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return

        if not self.songs.remove(song):
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

        if ctx.guild.id not in servers:
            await ctx.respond(
                "You can only use this bot in the pianovision server.", ephemeral=True
            )
            return

        if self.songs.rate(song,ctx.author.id, rating) == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
        else:
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



