import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm_client():
    """Initializes and returns the AzureOpenAI client."""
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not all([endpoint, api_key, deployment, api_version]):
        raise ValueError("Please set all AZURE_OPENAI environment variables.")

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        timeout=30.0,
        max_retries=1
    )

def chat_completion(messages: list[dict]) -> str:
    """
    Calls the Azure OpenAI LLM. This is a simple text-in, text-out call.
    The 'tools' and 'tool_choice' parameters are NOT used here.
    """
    client = get_llm_client()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=messages
            # No 'tools' or 'tool_choice'
        )
        # Return only the text content
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error calling Azure OpenAI: {e}")
        # Return a valid response structure for the parser to handle
        return f"<response>Sorry, I encountered an error: {e}</response><plan>[]</plan>"