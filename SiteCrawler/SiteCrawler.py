from agency_swarm.agents import Agent


class SiteCrawler(Agent):
    def __init__(self):
        super().__init__(
            name="SiteCrawler",
            description="Visits prioritized pages on business sites using Botasaurus",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
