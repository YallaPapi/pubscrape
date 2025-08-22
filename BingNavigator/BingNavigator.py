from agency_swarm.agents import Agent
from .tools.SerpFetchTool_requests import SerpFetchTool


class BingNavigator(Agent):
    def __init__(self):
        super().__init__(
            name="BingNavigator",
            description="Fetches Bing SERP pages via Botasaurus with anti-detection measures",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[SerpFetchTool],
        )

    def response_validator(self, message):
        return message
