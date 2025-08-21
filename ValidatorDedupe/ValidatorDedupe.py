from agency_swarm.agents import Agent


class ValidatorDedupe(Agent):
    def __init__(self):
        super().__init__(
            name="ValidatorDedupe",
            description="Validates email syntax, applies DNS checks, removes duplicates",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
