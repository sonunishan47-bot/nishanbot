import os
import streamlit as st
from groq import Groq
from .base import BaseAIProvider

class GroqProvider(BaseAIProvider):
    def __init__(self):
        # Streamlit Secrets-ൽ നിന്ന് API Key എടുക്കുന്നു
        self.api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            st.error("GROQ_API_KEY Streamlit Secrets-ൽ കാണുന്നില്ല!")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    def generate_response(self, prompt, system_prompt=None, history=None):
        if not self.client:
            return "Groq API Key ക്രമീകരിച്ചിട്ടില്ല."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for msg in history:
                messages.append(msg)

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Groq API Error: {str(e)}"
