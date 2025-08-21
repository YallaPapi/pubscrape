from agency_swarm.agents import Agent
from .tools.HtmlParserTool import HtmlParserTool


class SerpParser(Agent):
    def __init__(self):
        super().__init__(
            name="SerpParser",
            description="Parses SERP HTML files to extract business-relevant URLs",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[HtmlParserTool],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
