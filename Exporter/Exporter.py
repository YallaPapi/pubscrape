from agency_swarm.agents import Agent


class Exporter(Agent):
    def __init__(self):
        super().__init__(
            name="Exporter",
            description="Writes final CSV, JSON stats, error logs and reports",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
