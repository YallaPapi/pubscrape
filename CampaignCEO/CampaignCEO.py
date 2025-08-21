from agency_swarm.agents import Agent


class CampaignCEO(Agent):
    def __init__(self):
        super().__init__(
            name="CampaignCEO",
            description="Orchestrates campaigns and manages the entire lead generation pipeline",
            instructions="./instructions.md",
            files_folder="./files",
            schemas_folder="./schemas",
            tools=[],
            model="gpt-4-turbo-preview",
        )

    def response_validator(self, message):
        return message
