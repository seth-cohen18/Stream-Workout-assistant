# core/text_to_speech_manager.py
import pyttsx3
import threading

class TextToSpeechManager:
    def __init__(self):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if "female" in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def _speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def speak(self, text):
        thread = threading.Thread(target=self._speak, args=(text,))
        thread.daemon = True
        thread.start()
