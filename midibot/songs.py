from typing import Union
from mido import MidiFile
import os
import shutil
import uuid

import discord

from midibot import Store
from midibot import util


class Songs:
    class File:
        MIDI = ".mid"
        MUSESCORE = ".mscz"
        PIANOVISION = ".json"

    file_exts = [File.MIDI, File.MUSESCORE, File.PIANOVISION]

    class Type:
        VERIFIED = "verified"
        REQUESTED = "requested"
        UNVERIFIED = "unverified"

    all_types = [Type.VERIFIED, Type.REQUESTED, Type.UNVERIFIED]

    def __init__(self):
        self.songs = Store[list](f"data/songs.json", [])
        os.makedirs("data/songs", exist_ok=True)
        os.makedirs("data/output_files", exist_ok=True)

        for s in self.songs.data:
            if not s["type"] == Songs.Type.UNVERIFIED:
                s["type"] = Songs.Type.VERIFIED if Songs.File.MIDI in self.has_attachments(s) \
                    else Songs.Type.REQUESTED
            
            if "origin" not in s or s["origin"] == None:
                s["origin"] = ""

            if "version" not in s or s["version"] == None:
                s["version"] = ""

            if "meta" not in s or s["meta"] == None:
                s["meta"] = {}

            exts = self.has_attachments(s)
            for ext in exts:
                meta = self.update_metadata(s, ext)
                s["meta"][ext] = meta

        self.sync()

    @property
    def songlist(self):
        return [self.song_to_string(x) for x in self.songs.data]
    
    @property
    def songtuples(self):
        return tuple((self.song_to_string(x), x) for x in self.songs.data)

    def song_to_string(self, song_obj: dict) -> str:
        string = f'{song_obj["artist"]} - {song_obj["song"]}'
        if "version" in song_obj and song_obj["version"]:
            string = string + f' ({song_obj["version"]})'
        return string

    def get(self, songstring) -> Union[None, dict]:
        for song in self.songs.data:
            if self.song_to_string(song) == songstring:
                return song
        return None

    def sync(self):
        self.songs.sync()
    
    async def song_search(self, search_string: str, types: list[str] = all_types) -> list[str]:

        songs = self.songtuples
        search_string = search_string.lower()

        exact = [
            song[0]
            for song in songs
            if song[1]["type"] in types and search_string in song[0].lower()
        ]

        return exact

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
    
    def has_attachments(self, song_obj: dict) -> list:
        id = song_obj["id"]
        attachments = []

        for ext in Songs.file_exts:
            stored = f"data/songs/{id}{ext}"

            if os.path.exists(stored):
                attachments.append(ext)
        
        return attachments

    async def add_attachment(
        self, song_obj: dict, attachment: discord.Attachment
    ) -> Union[None, str]:

        for ext in Songs.file_exts:
            if attachment.filename.endswith(ext):
                stored = f'data/songs/{song_obj["id"]}{ext}'

                if os.path.exists(stored):
                    os.remove(stored)

                await attachment.save(stored)

                if song_obj["type"] == Songs.Type.REQUESTED and ext == Songs.File.MIDI:
                    song_obj["type"] = Songs.Type.UNVERIFIED
                
                meta = self.update_metadata(song_obj, ext)

                if (duplicate := self.find_duplicate(meta, ext)):
                    return f"This file is a duplicate. `{self.song_to_string(duplicate)}` already has this file attached."
                
                if "meta" not in song_obj or song_obj["meta"] == None:
                    song_obj["meta"] = {}
                
                song_obj["meta"][ext] = meta 

                self.sync()

                return None
            
        return "I don't know what to do with that file. Make sure it is one of the following types:\n" + ", ".join(Songs.file_exts)

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
    
    def add_song(self, song_data: dict) -> Union[None, str]:
        song_str = self.song_to_string(song_data)
        if song_str in self.songlist:
            return "Song already exists in my database"
        
        if song_data["origin"] and (duplicates := [x for x in self.songs.data if x["origin"] == song_data["origin"]]):
            if duplicates[0]["type"] == Songs.Type.REQUESTED:
                return "That song has already been requested."
            return "Song with that URL is already in my database."

        song_obj = self.__generate_new_song()
        song_obj.update(song_data)
        self.songs.data.append(song_obj)
        self.sync()

    def update(self, song_obj:dict, song_data: dict) -> Union[None, str]:
        song_str = self.song_to_string(song_data)
        if [x for x in self.songs.data if x is not song_obj and self.song_to_string(x) == song_str]:
            return "Song already exists in my database"
        
        if song_data["origin"] and [x for x in self.songs.data if x is not song_obj and x["origin"] == song_data["origin"]]:
            return "Song with that URL is already in my database"

        song_obj.update(song_data)
        self.sync()

    def verify(self, song_obj:dict):
        song_obj["type"] = Songs.Type.VERIFIED
        self.sync()

    def request_count(self) -> int:
        return len([
            x
            for x in self.songs.data
            if x["type"] == Songs.Type.REQUESTED
        ])
        
    def requests_for_user(self, user:int) -> int:
        return len([
            x
            for x in self.songs.data
            if x["type"] == Songs.Type.REQUESTED and
            "requested_by" in x and
            x["requested_by"] == user
        ])
    
    @staticmethod
    def update_metadata(song_obj, ext) -> dict:
        file = f'data/songs/{song_obj["id"]}{ext}'

        meta = {}
        meta["hash"] = util.hash(file)
        meta["size"] = os.path.getsize(file)

        if ext == Songs.File.MIDI:
            midi = MidiFile(file)
            meta["tracks"] = len(midi.tracks)

        return meta

    def find_duplicate(self, meta, ext) -> Union[dict, None]:        
        for song in self.songs.data:
            if "meta" in song and ext in song["meta"]:
                if Songs.meta_equal(meta, song["meta"][ext]):
                    return song
        return None
    
    @staticmethod
    def meta_equal(meta1, meta2) -> bool:
        return meta1["size"] == meta2["size"] and meta1["hash"] == meta2["hash"]