from agency_swarm.agents import Agent


class DomainClassifier(Agent):
    def __init__(self):
        super().__init__(
            name="DomainClassifier",
            description="Filters and prioritizes domains for business relevance",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
