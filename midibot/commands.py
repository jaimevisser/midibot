import logging
import os
import shutil
import uuid

import discord

from midibot import Store, SongModal
from discord import Cog, Option, slash_command


_log = logging.getLogger(__name__)

file_exts = [".mid", ".mscz", ".json"]

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
            string = string+f' ({song["version"]})'
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
        matching_sentences = [sentence for sentence in self.songlist if all(word in sentence.lower() for word in input_words)]

        return matching_sentences

    @slash_command()
    async def download(
        self,
        ctx,
        song: Option(
            str,
            "Song",
            autocomplete=song_search,
        )
    ):
        """Download files for a song"""
        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return
        
        id = song_obj["id"]
        files = []
        attachements = []
        for ext in file_exts:
            stored = f'data/songs/{id}{ext}'
            nice = f'data/output_files/{song}{ext}'

            if os.path.exists(stored):
                shutil.copy(stored,nice)
                files.append(nice)
                attachements.append(discord.File(nice))
        
        if len(attachements) > 0:
            await ctx.respond("There you go", files=attachements, ephemeral=True)
        else:
            await ctx.respond("No files attached to that song, use /upload to add them.", ephemeral=True)
        
        for f in files:
            os.remove(f)

    @slash_command()
    async def add(self, ctx):
        """Add a new song to the database"""
        modal = SongModal(self.add_new_song, title="Add a new song")
        await ctx.send_modal(modal)

    async def add_new_song(self, interaction: discord.Interaction, artist: str, song: str, version:str, origin:str):
        song = {
            "artist": artist,
            "song": song,
            "version": version if version != "" else None,
            "origin": origin if origin != "" else None,
            "id" : str(uuid.uuid4())
        }

        self.songs.data.append(song)
        self.songs.sync()
    
        await interaction.response.send_message("Song added", ephemeral=True)


    async def edit(self):
        pass

    @slash_command()
    async def upload(self, ctx, song: Option(
            str,
            "Song",
            autocomplete=song_search,
        )):
        """Upload files for a song"""

        song_obj = self.get_song(song)

        if song_obj == None:
            await ctx.respond("I don't know that song?", ephemeral=True)
            return

        await ctx.respond("Adding song files.\nSend a message with the files attached in the next 5 minutes.")

        def from_same_author(m: discord.Message):
            return m.author == ctx.author

        try:
            response: discord.Message = await self.bot.wait_for("message", check=from_same_author, timeout=60*5)
        except TimeoutError:
            return await ctx.send_followup("Sorry, you took too long. I stopped listening.")
        
        for a in response.attachments:
            for ext in file_exts:
                if a.filename.endswith(ext):
                    with open(f'data/songs/{song_obj["id"]}{ext}', 'wb') as file:
                        file.write(await a.read())
                    await ctx.send_followup(f"{ext} file added or replaced")


    async def remove(self):
        pass
