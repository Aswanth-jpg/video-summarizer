#!/usr/bin/env python3
"""
Test script to verify OpenAI API v1.0+ functionality
"""
from openai import OpenAI
import os

def test_openai_api():
    """Test OpenAI API with new v1.0+ syntax"""
    # Try to get API key from environment or secrets
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment variables")
        print("   Set your API key with: set OPENAI_API_KEY=your-key-here")
        return False
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        print("🔑 API key found, testing connection...")
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI API is working!' in exactly those words."}
            ],
            max_tokens=20,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ API Response: {result}")
        
        if "OpenAI API is working!" in result:
            print("🎉 OpenAI API is working correctly with v1.0+ syntax!")
            return True
        else:
            print("⚠️ API responded but with unexpected content")
            return False
            
    except Exception as e:
        print(f"❌ Error testing OpenAI API: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI API v1.0+ compatibility...")
    success = test_openai_api()
    
    if success:
        print("\n✅ Your YouTube Summarizer app should now work with OpenAI!")
    else:
        print("\n⚠️ Please check your OpenAI API key and try again.")
        print("   Make sure you have a valid API key from https://platform.openai.com/api-keys")