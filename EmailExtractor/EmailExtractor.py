from agency_swarm.agents import Agent


class EmailExtractor(Agent):
    def __init__(self):
        super().__init__(
            name="EmailExtractor",
            description="Extracts and scores emails from crawled HTML using multi-method detection",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
