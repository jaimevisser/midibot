import discord


class SongModal(discord.ui.Modal):
    def __init__(self, ext_callback, initial_values={}, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__ext_callback = ext_callback
        self.add_item(
            discord.ui.InputText(label="Artist", value=initial_values.get("artist"))
        )
        self.add_item(
            discord.ui.InputText(label="Song", value=initial_values.get("song"))
        )
        self.add_item(
            discord.ui.InputText(
                label="Version / additional info", value=initial_values.get("version"), required=False
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Origin (MuseScore or other URL)", value=initial_values.get("origin"), required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        songdata = {
            "artist": self.children[0].value.strip(),
            "song": self.children[1].value.strip(),
            "version": self.children[2].value.strip(),
            "origin": self.children[3].value.strip(),
        }

        await self.__ext_callback(
            interaction,
            songdata
        )
