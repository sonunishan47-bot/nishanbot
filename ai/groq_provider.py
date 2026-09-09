import os
import streamlit as st
from groq import Groq

class GroqProvider:
    def __init__(self):
        # Streamlit Secrets-ൽ നിന്നോ Environment Variable-ൽ നിന്നോ API Key എടുക്കുന്നു
        self.api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            st.error("Groq API Key കാണുന്നില്ല! Streamlit Secrets പരിശോധിക്കുക.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    def generate_response(self, messages, model="llama-3.3-70b-versatile"):
        if not self.client:
            return "API Key സെറ്റ് ചെയ്തിട്ടില്ല."
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Groq API Error: {str(e)}"
