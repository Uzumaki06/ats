import json
import os
from llama_cpp import Llama

llm = Llama(model_path = "OpenBioLLM-Llama3-8B.Q4_K_M.gguf",
            chat_format = "llama-2",
            cpu_threads = os.cpu_count()/2,
            n_ctx = 4096
            )

def summarize_text(transcription):
    try:
        
        result = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are a helpful assistant that generates HIPAA-compliant summaries for medical transcriptions. 
                        Ensure that all identifiable patient information is removed. The summary should be concise yet 
                        detailed enough to convey essential information from the medical notes/history, providing a 
                        clear understanding of the content in paragraph form without omitting critical details.
                    """
                },
                {
                    "role": "user",
                    "content": "Generate a HIPAA-compliant summary for the following transcription: " + transcription
                }
            ]
        )
        # Return only the summary from the chat completion
        return json.loads(result["choices"][0]["message"]["content"])["summary"], None
    except Exception as e:
        return None, str(e)