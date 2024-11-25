from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, HttpUrl
import requests
import secrets
import tempfile
import os

# Initialize FastAPI app
app = FastAPI()

# User API key database (example)
USER_API_KEYS = {
    # Example API key for demonstration
    "jh-7c6a2e4bcd9f4c6e9a85e356d6fb43e12dc1e2c174e947f0f15e4d927bc9f91c": "User1"
}

# Function to generate an API key
def generate_api_key_with_prefix():
    """
    Generate an API key prefixed with 'jh-'.
    Returns:
        str: A randomly generated API key in the format 'jh-apikey'.
    """
    api_key = secrets.token_hex(32)  # Generate a 64-character hexadecimal key
    return f"jh-{api_key}"  # Add the 'jh-' prefix

# Dependency to authenticate user
def authenticate_user(jh_apikey: str = Header(...)):
    """
    Authenticate the user based on the API key in the 'jh-apikey' format.
    """
    user = USER_API_KEYS.get(jh_apikey)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key in 'jh-apikey' header")
    return user

# Pydantic model for file link input
class FileLink(BaseModel):
    file_url: HttpUrl

@app.post("/upload-audio/")
async def upload_audio(file_link: FileLink, current_user: str = Depends(authenticate_user)):
    """
    Endpoint to upload audio files via a link, transcribe, and summarize.
    """
    # Download the file from the provided link
    try:
        response = requests.get(file_link.file_url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error downloading file: {e}")

    # Save the file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(response.content)
        temp_audio_path = temp_audio.name

    try:
        # Transcribe audio (dummy function for example)
        transcription_text = f"Transcribed text from {temp_audio_path}"  # Replace with actual logic
    except Exception as e:
        os.remove(temp_audio_path)  # Cleanup on failure
        raise HTTPException(status_code=500, detail=f"Error in transcription: {e}")

    # Clean up temporary file
    os.remove(temp_audio_path)

    return {"transcription": transcription_text, "user": current_user}

@app.post("/summarize/")
async def summarize(request: BaseModel, current_user: str = Depends(authenticate_user)):
    """
    Endpoint for summarizing text.
    """
    text_to_summarize = request.dict().get("text")
    if not text_to_summarize:
        raise HTTPException(status_code=400, detail="Text field is required for summarization.")

    try:
        # Summarize text (dummy function for example)
        summary = f"Summary of: {text_to_summarize}"  # Replace with actual logic
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in summarization: {e}")

    return {"summary": summary, "user": current_user}

@app.get("/generate-api-key/")
async def generate_api_key_endpoint():
    """
    Endpoint to generate a new API key (for admin use).
    """
    new_api_key = generate_api_key_with_prefix()
    return {"api_key": new_api_key}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
