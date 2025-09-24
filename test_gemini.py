#!/usr/bin/env python3
"""
Test script to verify Google Gemini API functionality
"""
import google.generativeai as genai
import os
from pathlib import Path


def load_env_file():
    """Load environment variables from .env file.

    Checks current working directory first, then the script directory.
    Handles UTF-8 with BOM files.
    """
    candidate_paths = [
        Path.cwd() / '.env',
        Path(__file__).resolve().parent / '.env',
    ]

    for env_path in candidate_paths:
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip().lstrip('\ufeff')
                            value = value.strip().strip("'\"")
                            os.environ[key] = value
            except Exception:
                # Try next candidate on error
                continue
            # Stop after first successful load
            break


# Load environment variables from .env file
load_env_file()


def test_gemini_api():
    """Test Gemini API functionality"""
    # Try to get API key from environment or secrets
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ No GEMINI_API_KEY found in environment variables")
        print("   Set your API key with: set GEMINI_API_KEY=your-key-here")
        print("   Get your key from: https://aistudio.google.com/app/apikey")
        return False
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        print("🔑 API key found, testing connection...")
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test with a simple prompt
        response = model.generate_content(
            "Say 'Gemini API is working!' in exactly those words.",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=20,
                temperature=0,
            )
        )
        
        result = response.text.strip()
        print(f"✅ API Response: {result}")
        
        if "Gemini API is working!" in result:
            print("🎉 Gemini API is working correctly!")
            return True
        else:
            print("⚠️ API responded but with unexpected content")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        return False


if __name__ == "__main__":
    print("Testing Google Gemini API...")
    success = test_gemini_api()
    
    if success:
        print("\n✅ Your YouTube Summarizer app should now work with Gemini!")
    else:
        print("\n⚠️ Please check your Gemini API key and try again.")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")