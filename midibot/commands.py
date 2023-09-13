import logging
import os
import shutil
import uuid

import discord

from midibot import Store, SongModal
from discord import Cog, Option, guild_only, slash_command
from discord.commands import default_permissions


_log = logging.getLogger(__name__)

file_exts = [".mid", ".mscz", ".json"]

servers = [1004388945422987304, 908282497769558036]


class Commands(Cog):
    def __init__(self, bot: discord.Bot):
        self.songs = Store[list](f"data/songs.json", [])
        self.bot = bot
        os.makedirs("data/songs", exist_ok=True)
        os.makedirs("data/output_files", exist_ok=True)

    @property
    def songlist(self):
        return [self.song_to_string(x) for x in self.songs.data]

    def song_to_string(self, song):
        string = f'{song["artist"]} - {song["song"]}'
        if song["version"] is not None and song["version"] != "":
            string = string + f' ({song["version"]})'
        return string

    def get_song(self, songstring):
        for song in self.songs.data:
            if self.song_to_string(song) == songstring:
                return song
        return None

    async def song_search(self, ctx: discord.AutocompleteContext):
        # Split the input string into lowercase words
        input_words = ctx.value.lower().split()

        # Filter the sentences that contain all input words (case-insensitive)
        matching_sentences = [
            sentence
            for sentence in self.songlist
            if all(word in sentence.lower() for word in input_words)
        ]

        return matching_sentences

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
        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        id = song_obj["id"]
        files = []
        attachements = []
        for ext in file_exts:
            stored = f"data/songs/{id}{ext}"
            nice = f"data/output_files/{song}{ext}"

            if os.path.exists(stored):
                shutil.copy(stored, nice)
                files.append(nice)
                attachements.append(discord.File(nice))

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
            }

            self.songs.data.append(song)
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

            self.songs.sync

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

        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        for ext in file_exts:
            if file.filename.endswith(ext):
                stored = f'data/songs/{song_obj["id"]}{ext}'
                if os.path.exists(stored):
                    os.remove(stored)

                await file.save(stored)
                await ctx.respond(f"{ext} file added or replaced", ephemeral=True)
                return

        await ctx.respond(
            "I don't know what to do with that file. Make sure it is one of the following types: "
            + ", ".join(file_exts),
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

        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        id = song_obj["id"]
        for ext in file_exts:
            stored = f"data/songs/{id}{ext}"

            if os.path.exists(stored):
                os.remove(stored)

        self.songs.data.remove(song_obj)
        self.songs.sync()

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

        song_obj: dict = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return
        
        if "ratings" not in song_obj:
            song_obj["ratings"] = {}

        song_obj["ratings"][f"{ctx.author.id}"] = rating
        ratings = list(song_obj["ratings"].values())
        song_obj["rating"] = float(sum(ratings)) / len(ratings)

        self.songs.sync()

        await ctx.respond("Your rating has been added, thanks!", ephemeral=True)


    @slash_command()
    @guild_only()
    async def list(self, ctx: discord.ApplicationContext):
        """Get a list of the top rated songs."""

        def songsorter(song: dict):
            return song.get("rating", float(0))

        sorted = self.songs.data.copy()
        sorted.sort(key=songsorter, reverse=True)

        list = ""

        for song in sorted[0:50]:
            list += f'{song.get("rating", float(0))} : {self.song_to_string(song)}'

        await ctx.respond(list, ephemeral=True)



