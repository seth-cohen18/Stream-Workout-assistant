# core/text_to_speech_manager.py
import pyttsx3
import threading
import time

class TextToSpeechManager:
    def __init__(self):
        self.engine = None
        self.init_engine()
        self.last_spoken = {}
        self.lock = threading.Lock()
        
    def init_engine(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            # Try to select a female voice
            female_voice = None
            for voice in voices:
                if "female" in voice.name.lower():
                    female_voice = voice.id
                    break
            
            if female_voice:
                self.engine.setProperty('voice', female_voice)
                
            # Set properties
            self.engine.setProperty('rate', 150)  # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume (0-1)
            
            return True
        except Exception as e:
            print(f"Text-to-speech initialization error: {e}")
            self.engine = None
            return False

    def _speak(self, text):
        if not self.engine:
            success = self.init_engine()
            if not success:
                print("Failed to initialize text-to-speech engine")
                return
                
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Text-to-speech error: {e}")
            # Try to reinitialize the engine
            self.init_engine()

    def speak(self, text, cooldown=5):
        """
        Speak text with a cooldown to prevent repeated messages.
        
        Args:
            text: Text to speak
            cooldown: Minimum seconds between repeating the same message
        """
        current_time = time.time()
        
        with self.lock:
            # Check if this exact message has been spoken recently
            if text in self.last_spoken:
                last_time = self.last_spoken[text]
                if current_time - last_time < cooldown:
                    return  # Skip if said too recently
            
            # Update the last spoken time
            self.last_spoken[text] = current_time
        
        # Start a new thread to speak the text
        thread = threading.Thread(target=self._speak, args=(text,))
        thread.daemon = True
        thread.start()