import os
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

# Extract base endpoint (remove /openai/deployments/... path)
full_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
base_endpoint = full_endpoint.split("/openai/deployments")[0] if "/openai/deployments" in full_endpoint else full_endpoint


class AzureClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=base_endpoint,
            api_key=os.getenv("AZURE_OPENAI_KEY"),
        )

  
    def call_llm(self, message: list, temp: float=0.0):
        response = self.client.chat.completions.create(
            messages=message,
            max_tokens=4096,
            temperature=temp,
            top_p=1.0,
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )

        return(response.choices[0].message.content)