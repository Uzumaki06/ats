from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, HttpUrl
import requests
import tempfile
import os
import secrets
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from transcribe import transcribe_audio  
from summarize import summarize_text 

# Initialize FastAPI app
app = FastAPI()

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017"
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.transcription_db
transcriptions_collection = db.transcriptions
api_keys_collection = db.api_keys

# Function to generate an API key
def generate_api_key_with_prefix():
    """
    Generate an API key prefixed with 'jh-'.
    """
    api_key = secrets.token_hex(32)
    return f"jh-{api_key}"

# Dependency to authenticate user
async def authenticate_user(jh_apikey: str = Header(...)):
    """
    Authenticate the user using the API key stored in the database.
    """
    user = await api_keys_collection.find_one({"api_key": jh_apikey})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key in 'jh-apikey' header")
    return user["user"]

# Pydantic models
class FileLink(BaseModel):
    file_url: HttpUrl

class SummarizeRequest(BaseModel):
    text: str = None
    transcription_id: str = None

@app.post("/upload-audio/")
async def upload_audio(file_link: FileLink, current_user: str = Depends(authenticate_user)):
    """
    Upload an audio file via URL, transcribe it, and store the transcription in MongoDB.
    """
    # Download the file
    try:
        response = requests.get(file_link.file_url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error downloading file: {e}")

    # Save the file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
        temp_audio.write(response.content)
        temp_audio_path = temp_audio.name

    try:
        # Transcribe the audio
        transcription_text = transcribe_audio(temp_audio_path) 
    except Exception as e:
        os.remove(temp_audio_path)  # Cleanup on failure
        raise HTTPException(status_code=500, detail=f"Error in transcription: {e}")

    # Clean up temporary file
    os.remove(temp_audio_path)

    # Save transcription to MongoDB
    transcription_data = {
        "text": transcription_text,
        "user": current_user,
    }
    result = await transcriptions_collection.insert_one(transcription_data)
    transcription_id = str(result.inserted_id)

    return {"transcription_id": transcription_id, "transcription": transcription_text}

@app.post("/summarize/")
async def summarize(request: SummarizeRequest, current_user: str = Depends(authenticate_user)):
    """
    Summarize text provided directly or associated with a transcription ID.
    """
    if not request.text and not request.transcription_id:
        raise HTTPException(status_code=400, detail="Provide either text or transcription_id.")

    text_to_summarize = request.text
    if request.transcription_id:
        # Retrieve transcription from MongoDB
        transcription = await transcriptions_collection.find_one(
            {"_id": ObjectId(request.transcription_id), "user": current_user}
        )
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found.")
        text_to_summarize = transcription["text"]

    try:
        # Summarize the text
        summary = summarize_text(text_to_summarize)  # Actual summarization logic
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in summarization: {e}")

    return {"summary": summary}

@app.post("/generate-api-key/")
async def generate_api_key_endpoint(username: str):
    """
    Generate and store a new API key for a user in MongoDB.
    """
    new_api_key = generate_api_key_with_prefix()
    api_key_data = {"user": username, "api_key": new_api_key}
    await api_keys_collection.insert_one(api_key_data)
    return {"api_key": new_api_key}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
