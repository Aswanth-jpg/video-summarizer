import whisper
import torch
if torch.cuda.is_available():
    print("CUDA is available. Using GPU.")
model_path = "base.pt"
audio_path = "audio.mp3"
model = whisper.load_model(model_path)
result = model.transcribe(audio_path, fp16=False)
print(result["text"])