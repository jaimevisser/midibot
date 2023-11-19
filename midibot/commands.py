import logging
import os
import shutil
from typing import Union
import uuid

import discord

from midibot import SongModal, Songs
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
    
    async def song_search_unverified(self, ctx: discord.AutocompleteContext):
        return await self.songs.song_search_unverified(ctx.value)

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
        if not (song_obj := await self.get_song(ctx, song)):
            return

        await self.download_song(ctx, song_obj)

    async def download_song(self, ctx, song_obj: dict, ephemeral = True):
        song_obj = self.songs.get_attachements(song_obj)

        (files, attachements) = song_obj

        if len(attachements) > 0:
            await ctx.respond("There you go", files=attachements, ephemeral=ephemeral)
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
        if await self.wrong_server(ctx):
            return

        async def add_new_song(interaction: discord.Interaction, data: dict):
            data["added_by"] = ctx.author.id
            data["type"] = Songs.Type.VERIFIED
            if error := self.songs.add_song(data):
                await interaction.response.send_message(error, ephemeral=True)
                return

            await interaction.response.send_message("Song added", ephemeral=True)

        modal = SongModal(add_new_song, title="Add a new song")
        await ctx.send_modal(modal)

    @slash_command()
    @guild_only()
    @default_permissions(administrator=True)
    async def request(self, ctx: discord.ApplicationContext):
        """Request a song."""
        if await self.wrong_server(ctx):
            return

        async def add_new_song(interaction: discord.Interaction, data: dict):
            data["requested_by"] = ctx.author.id
            data["type"] = Songs.Type.REQUESTED
            if error := self.songs.add_song(data):
                await interaction.response.send_message(error, ephemeral=True)
                return

            await interaction.response.send_message(
                f'Song "{self.songs.song_to_string(data)}" requested by <@{ctx.author.id}>.'
            )

        modal = SongModal(add_new_song, title="Request a song")
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
        if await self.wrong_server(ctx):
            return
        if not (song_obj := await self.get_song(ctx, song)):
            return

        async def update_song(interaction: discord.Interaction, data: dict):
            if error := self.songs.update(song_obj, data):
                await interaction.response.send_message(error, ephemeral=True)
                return
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
        file: discord.Attachment,
    ):
        """Upload files for a song."""
        if await self.wrong_server(ctx):
            return
        if not (song_obj := await self.get_song(ctx, song)):
            return

        was_requested = song_obj["type"] == Songs.Type.REQUESTED

        saved = await self.songs.add_attachment(song_obj, file)

        if saved is True:
            await ctx.respond(f"File added or replaced", ephemeral=True)
        if saved is False:
            await ctx.respond(
                "I don't know what to do with that file. Make sure it is one of the following types:\n"
                + ", ".join(Songs.file_exts),
                ephemeral=True,
            )

        if (
            was_requested
            and song_obj["type"] == Songs.Type.UNVERIFIED
            and "requested_by" in song_obj
        ):
            await ctx.respond(
                f"Hey <@{song_obj['requested_by']}>, your song has been uploaded by <@{ctx.author.id}>!\n"+
                "Make sure to use `/verify` if you have tested it in PianoVision and it works!"
            )
            await self.download_song(ctx, song_obj, ephemeral=False)

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
        if await self.wrong_server(ctx):
            return
        if not (song_obj := await self.get_song(ctx, song)):
            return

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
        rating: Option(int, "Rating from 0 to 5", min_value=0, max_value=5),
    ):
        """Rate a song"""
        if await self.wrong_server(ctx):
            return
        if not (song_obj := await self.get_song(ctx, song)):
            return

        self.songs.rate(song_obj, ctx.author.id, rating)
        await ctx.respond("Your rating has been added, thanks!", ephemeral=True)

    @slash_command()
    @guild_only()
    async def list(
        self,
        ctx: discord.ApplicationContext,
        filter: Option(
            str,
            "Filter the list",
            choices=["verified", "unverified"],
            default="verified",
        ),
    ):
        """Get a list of all songs. By default only shows verified songs."""
        if await self.wrong_server(ctx):
            return

        def songsorter(song: dict):
            return song.get("rating", float(0))

        sorted = self.songs.songs.data.copy()
        sorted = [x for x in sorted if x["type"] == filter]
        sorted.sort(key=songsorter, reverse=True)

        chunk_size = 20

        chunked = [
            sorted[i : i + chunk_size] for i in range(0, len(sorted), chunk_size)
        ]

        await ctx.respond(
            "**Legend**\n"
            + ":musical_note: : MuseScore file\n"
            + ":musical_keyboard: : Midi file",
            ephemeral=True,
        )

        for songs in chunked:
            list = ""

            for song in songs:
                attachments = self.songs.has_attachments(song)

                ext = ""
                ext += (
                    ":musical_note:"
                    if Songs.File.MUSESCORE in attachments
                    else ":black_large_square:"
                )
                ext += (
                    ":musical_keyboard:"
                    if Songs.File.MIDI in attachments
                    else ":black_large_square:"
                )

                list += f'{song.get("rating", float(0))} {ext} : {self.songs.song_to_string(song)}\n'

            await ctx.respond(list, ephemeral=True)

    @slash_command()
    @guild_only()
    async def open_requests(
        self,
        ctx: discord.ApplicationContext,
    ):
        """Get a list of all open song requests."""
        if await self.wrong_server(ctx):
            return

        sorted = [
            x
            for x in self.songs.songs.data
            if x["type"] == Songs.Type.REQUESTED and x["origin"]
        ]
        sorted += [
            x
            for x in self.songs.songs.data
            if x["type"] == Songs.Type.REQUESTED and not x["origin"]
        ]

        chunk_size = 20

        chunked = [
            sorted[i : i + chunk_size] for i in range(0, len(sorted), chunk_size)
        ]

        for songs in chunked:
            list = ""

            for song in songs:
                list += f'{self.songs.song_to_string(song)} {song["origin"]}\n'

            await ctx.respond(list, ephemeral=True)

    @slash_command()
    @guild_only()
    async def verify(
        self,
        ctx: discord.ApplicationContext,
        song: Option(
            str,
            "Song",
            autocomplete=song_search_unverified,
        )
    ):
        """Verify a song works in PianoVision."""
        if await self.wrong_server(ctx):
            return
        if not (song_obj := await self.get_song(ctx, song)):
            return
        
        self.songs.verify(song_obj)

        await ctx.respond(f"<@{ctx.author.id}> has verified that \"{self.songs.song_to_string(song_obj)}\" works in PianoVision! Thanks!")

    @slash_command()
    @guild_only()
    async def midibot_help(
        self,
        ctx: discord.ApplicationContext
    ):
        """Help!"""
        await ctx.respond(
            "**Midibot help!**\n"+
            "Midibot is here to help you find midi files to play with PianoVision, or to request files you want to play.\n"+
            "*The following commands are available:*\n\n"+
            "`/list`: List songs in Midibot, by default only shows verified songs but you can change the filter option if you want.\n"+
            "`/download`: Download a song, start typing in the song option to find the song you are looking for.\n"+
            "`/request`: Request a song. Adding a MuseScore URL gives you priority over songs that don't have an URL.\n"+
            "`/open_requests`: View all open requests, the ones listed first have been waiting the longest.\n"+
            "`/upload`: Upload midi, MuseScore or PianoVision json files for a song.\n"+
            "`/verify`: Verify that an uploaded song works in PianoVision.\n"+
            "`/add`: Add a song to the MidiBot database, I'll assume you have verified it works. Add the files afterwards with `/upload`.\n"+
            "`/rate`: Give a song a rating from 0-5. Songs with higher ratings appear higher in the `/list`."
        )