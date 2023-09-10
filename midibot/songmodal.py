import discord


class SongModal(discord.ui.Modal):
    def __init__(self, ext_callback, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__ext_callback = ext_callback
        self.add_item(discord.ui.InputText(label="Artist"))
        self.add_item(discord.ui.InputText(label="Song"))
        self.add_item(discord.ui.InputText(label="Version", required=False))
        self.add_item(discord.ui.InputText(label="Origin (URL)", required=False))

    async def callback(self, interaction: discord.Interaction):
        await self.__ext_callback(interaction, 
                                  self.children[0].value.strip(), 
                                  self.children[1].value.strip(), 
                                  self.children[2].value.strip(),
                                  self.children[3].value.strip())