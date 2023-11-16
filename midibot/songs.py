from typing import Union
import os
import shutil
import uuid

import discord

from midibot import Store


class Songs:
    file_exts = [".mid", ".mscz", ".json"]

    def __init__(self):
        self.songs = Store[list](f"data/songs.json", [])
        os.makedirs("data/songs", exist_ok=True)
        os.makedirs("data/output_files", exist_ok=True)

        migrate = [x for x in self.songs.data if "type" not in x]

        if migrate:
            for s in migrate:
                s["type"] = "verified"
            self.sync()

    @property
    def songlist(self):
        return [self.song_to_string(x) for x in self.songs.data]

    def song_to_string(self, song_obj: dict) -> str:
        string = f'{song_obj["artist"]} - {song_obj["song"]}'
        if song_obj["version"] is not None and song_obj["version"] != "":
            string = string + f' ({song_obj["version"]})'
        return string

    def get(self, songstring) -> Union[None, dict]:
        for song in self.songs.data:
            if self.song_to_string(song) == songstring:
                return song
        return None

    def sync(self):
        self.songs.sync()

    async def song_search(self, search_string: str) -> list[str]:
        input_words = search_string.lower().split()

        songs = [
            song
            for song in self.songlist
            if all(word in song.lower() for word in input_words)
        ]

        return songs

    def get_attachements(
        self, song_obj: dict
    ) -> Union[None, tuple[list[discord.File], list[str]]]:

        id = song_obj["id"]
        files: list[str] = []
        attachements: list[discord.File] = []

        for ext in Songs.file_exts:
            stored = f"data/songs/{id}{ext}"
            nice = f"data/output_files/{self.song_to_string(song_obj)}{ext}"

            if os.path.exists(stored):
                shutil.copy(stored, nice)
                files.append(nice)
                attachements.append(discord.File(nice))

        return (files, attachements)

    async def add_attachment(
        self, song_obj: dict, attachment: discord.Attachment
    ) -> Union[None, bool]:

        for ext in Songs.file_exts:
            if attachment.filename.endswith(ext):
                stored = f'data/songs/{song_obj["id"]}{ext}'
                if os.path.exists(stored):
                    os.remove(stored)

                await attachment.save(stored)
                return True
        return False

    def remove(self, song_obj:dict) -> bool:

        if song_obj == None:
            return False

        id = song_obj["id"]
        for ext in Songs.file_exts:
            stored = f"data/songs/{id}{ext}"

            if os.path.exists(stored):
                os.remove(stored)

        self.songs.data.remove(song_obj)
        self.songs.sync()
        return True

    def rate(self, song_obj: dict, userid: int, rating: int) -> None:
        if 5 < rating < 0:
            return False

        if "ratings" not in song_obj:
            song_obj["ratings"] = {}

        song_obj["ratings"][f"{userid}"] = rating
        ratings = list(song_obj["ratings"].values())
        song_obj["rating"] = float(sum(ratings)) / len(ratings)

        self.songs.sync()
        return True
    
    def __generate_new_song(self) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "type": "verified"
        }
    
    def add_song(self, song_data: dict):
        song_obj = self.__generate_new_song()
        song_obj.update(song_data)
        self.songs.data.append(song_obj)
        self.sync()

    def update(self, song_obj:dict, song_data: dict) -> bool:
        song_obj.update(song_data)
        self.songs.sync()
        return True
        
