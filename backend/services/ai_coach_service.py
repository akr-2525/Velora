import google.generativeai as genai
import os
import json
import random
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Configure the API key securely
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the latest lightning-fast 2.5 flash model
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_daily_digest(user_name: str, user_goals: str):
    themes = [
        "Overcoming imposter syndrome when learning hard concepts", 
        "Time-blocking, deep work, and absolute focus", 
        "Breaking massive, intimidating goals into micro-steps",
        "Maintaining discipline when motivation completely fades",
        "The power of incremental daily progress (the 1% rule)"
    ]
    daily_theme = random.choice(themes)
    
    prompt = f"""
    You are a world-class technical mentor and executive coach. 
    Write a daily motivational digest for {user_name}. 
    Their specific long-term goal is: "{user_goals}".
    Today's core theme must be: "{daily_theme}".
    
    Do not use cliché advice. Provide actionable, unique, and highly specific insights. 
    
    CRITICAL INSTRUCTION TO AVOID COPYRIGHT: 
    For the "quote" field, DO NOT use real quotes from real people. 
    Invent a profound, original philosophical statement yourself, and attribute it to a fictional "Senior AI Engineer" or "Anonymous Developer".
    
    You must format your response with these exact keys: quote, author, tip, habit_reminder.
    """
    
    try:
        # NATIVE JSON MODE: This forces Gemini to ONLY return a dictionary!
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
            
        # Convert the string directly into a real Python dictionary
        digest_data = json.loads(response.text.strip())
        
        # Final safety check
        if not isinstance(digest_data, dict):
            raise ValueError("Data is not a dictionary")
            
        return digest_data
        
    except Exception as e:
        print(f"⚠️ API or Parsing Error: {e}")
        # Fallback data so the email scheduler NEVER crashes
        return {
            "quote": "The code you write today is the foundation for the engineer you become tomorrow.",
            "author": "System Fallback",
            "tip": "Take a 5-minute walk away from your keyboard. Your brain solves complex algorithmic problems in the background when you step away from the screen.",
            "habit_reminder": "Spend 10 minutes reviewing the core concepts of your current goal."
        }