import os
import streamlit as st
from groq import Groq

class GroqProvider:
    def __init__(self):
        self.api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            st.error("GROQ_API_KEY കാണുന്നില്ല!")
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
            return f"Groq Error: {str(e)}"

# ui/chat.py നേരിട്ട് വിളിക്കുന്നത് ഈ ഫംഗ്ഷനെയാണ്!
def get_provider(provider_type="groq"):
    return GroqProvider()

class AIProviderFactory:
    @staticmethod
    def get_provider(provider_type="groq"):
        return get_provider(provider_type)
