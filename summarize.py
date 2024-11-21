import os
from llama_cpp import Llama
from transcribe import transcribe_audio

# Initialize Llama model
llm = Llama(
    model_path="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    chat_format="llama-3",
    cpu_threads=os.cpu_count() // 2,
    n_ctx=4096
)

def summarize_text(transcription):
    try:
        result = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are a helpful assistant that generates HIPAA-compliant summaries for medical transcriptions. 
                        Ensure that all identifiable patient information is removed. The summary should be a concise 
                        overview that captures essential information without timestamps or specific routine details. 
                        Provide a short paragraph that highlights the overall condition and care actions relevant to the 
                        patient's status and any notable changes.
                    """
                },
                {
                    "role": "user",
                    "content": "Generate a brief, HIPAA-compliant summary for the following text: " + transcription
                }
            ]
        )
        
        # Check if result is as expected
        output_content = result["choices"][0]["message"]["content"].strip()
        if not output_content:
            return None, "Received empty response from model"
        
        # Return the plain text summary
        return output_content, None

    except Exception as e:
        return None, f"Error in summarization: {str(e)}"
