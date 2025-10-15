# filename: tools/sequence_function_tool.py
# Description: Defines a custom LangChain tool to query our sequence-to-function knowledge base API.

import httpx
from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

# Define the input schema for the tool using Pydantic.
# This ensures that the agent provides a correctly formatted input.
class SequenceFunctionInput(BaseModel):
    query: str = Field(description="A specific question about a protein's function, variants, or domains.")

class SequenceFunctionTool(BaseTool):
    """
    A tool to answer questions about the function of protein variants,
    modifications, or domains as they relate to aging and longevity.
    """

    # 1. DEFINE THE TOOL'S IDENTITY
    name: str = "sequence_function_knowledge_base"
    description: str = (
        "Use this tool to answer questions about the specific functions of protein variants, "
        "modifications, or domains, especially as they relate to aging and longevity. "
        "The input should be a specific, natural language question about a protein."
    )
    args_schema: Type[BaseModel] = SequenceFunctionInput

    # 2. DEFINE THE TOOL'S ACTION (_run method)
    def _run(self, query: str) -> str:
        """
        This method is called by the agent to execute the tool.
        It makes an API call to our production FastAPI server.
        """
        # --- This is where you connect to your deployed FastAPI server ---
        # For now, we'll use a placeholder URL.
        api_base_url = "http://localhost:8000" # Replace with your production URL later
        endpoint = "/query"
        full_url = f"{api_base_url}{endpoint}"
        
        print(f"Tool executing: Calling API at {full_url} with query: '{query}'")

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(full_url, json={"query": query})
                response.raise_for_status() # Raise an exception for HTTP errors
                
                # Assuming the API returns a JSON with an "answer" key
                result = response.json()
                return result.get("answer", "No answer found.")
        except httpx.RequestError as e:
            return f"Error: Could not connect to the knowledge base API. {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    # 3. DEFINE ASYNC ACTION (Optional but good practice)
    async def _arun(self, query: str) -> str:
        """Asynchronous version of the _run method."""
        api_base_url = "http://localhost:8000"
        endpoint = "/query"
        full_url = f"{api_base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(full_url, json={"query": query})
                response.raise_for_status()
                result = response.json()
                return result.get("answer", "No answer found.")
        except httpx.RequestError as e:
            return f"Error: Could not connect to the knowledge base API. {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

# --- Example of how to use this tool in another script ---
if __name__ == "__main__":
    # This part is just for testing the tool directly.
    print("Testing the SequenceFunctionTool directly...")
    tool = SequenceFunctionTool()
    
    # Simulate a query that an agent might make
    test_query = "What is the function of the SIRT6 centenarian variant?"
    
    # Run the tool's logic
    result = tool.invoke({"query": test_query}) # Use .invoke() for the new LangChain syntax
    
    print("\n--- Tool Test Result ---")
    print(result)

    # for example, in backend/main.py
    # from core_logic.tools.sequence_function_tool import SequenceFunctionTool
    # rest of FastAPI app code...
