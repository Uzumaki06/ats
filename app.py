from fastapi import FastAPI, HTTPException,UploadFile,File
from pydantic import BaseModel
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import tempfile
import os
from transcribe import transcribe_audio
from threading import Thread
from summarize import summarize_text

app = FastAPI()

fs = 44100  # Sample rate
recording = []
recording_stream = None
is_recording = False
is_paused = False

class SummarizationRequest(BaseModel):
    text: str

@app.post("/upload-audio/")
async def upload_audio(file: UploadFile = File(...)):
    """Endpoint for uploading audio files to transcribe and summarize."""
    if file.content_type not in ["audio/wav", "audio/mp3"]:
        raise HTTPException(status_code=400, detail="Invalid file format. Only WAV or MP3 files are accepted.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name

    transcription_text, error = transcribe_audio(temp_audio_path)
    os.remove(temp_audio_path) 

    if error:
        raise HTTPException(status_code=500, detail=f"Error in transcription: {error}")
    
    return {"transcription": transcription_text}

@app.post("/summarize/")
async def summarize(request: SummarizationRequest):
    """Endpoint for summarizing transcribed text."""
    summary, error = summarize_text(request.text)
    if error:
        raise HTTPException(status_code=500, detail=f"Error in summarization: {error}")
    
    return {"summary": summary}

@app.post("/start-recording/")
async def start_recording():
    """Start recording audio."""
    global is_recording, is_paused, recording, recording_stream

    if is_recording:
        raise HTTPException(status_code=400, detail="Recording is already in progress.")
    
    is_recording = True
    is_paused = False
    recording = [] 

    def record_audio():
        global recording, is_recording, is_paused
        with sd.InputStream(samplerate=fs, channels=1) as stream:
            while is_recording:
                if not is_paused:
                    buffer = stream.read(1024)[0]
                    recording.append(buffer)

    recording_thread = Thread(target=record_audio)
    recording_thread.start()
    return {"message": "Recording started."}

@app.post("/pause-recording/")
async def pause_recording():
    """Pause audio recording."""
    global is_paused, is_recording

    if not is_recording:
        raise HTTPException(status_code=400, detail="No recording in progress to pause.")
    if is_paused:
        raise HTTPException(status_code=400, detail="Recording is already paused.")

    is_paused = True
    return {"message": "Recording paused."}

@app.post("/resume-recording/")
async def resume_recording():
    """Resume audio recording."""
    global is_paused, is_recording

    if not is_recording:
        raise HTTPException(status_code=400, detail="No recording in progress to resume.")
    if not is_paused:
        raise HTTPException(status_code=400, detail="Recording is already running.")

    is_paused = False
    return {"message": "Recording resumed."}

@app.post("/stop-recording/")
async def stop_recording():
    """Stop recording audio and process the recorded data."""
    global is_recording, is_paused, recording

    if not is_recording:
        raise HTTPException(status_code=400, detail="No recording is in progress.")

    is_recording = False
    is_paused = False

    # Combine recorded buffers into a single array
    recording_data = np.concatenate(recording, axis=0)

    # Save the recording to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
        wav.write(temp_audio_file.name, fs, recording_data.astype(np.float32))
        audio_path = temp_audio_file.name

    # Transcribe the audio
    transcription_text, error = transcribe_audio(audio_path)
    os.remove(audio_path)  

    if error:
        raise HTTPException(status_code=500, detail=f"Error in transcription: {error}")
    
    return {"transcription": transcription_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
