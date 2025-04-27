#!/usr/bin/env python3
import os
import sys
import json
from dotenv import load_dotenv
import traceback

# Import the chatbot code
# Note: We've modified the original chatbot code to be callable as a module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from water_watch_chatbot import CommunityWaterWatchChatbot

def main():
    # Load environment variables
    load_dotenv()
    
    # Check if Google API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        result = {
            "response": "Error: Google API Key is not set. Please configure your .env file.",
            "success": False
        }
        print(json.dumps(result))
        return
    
    try:
        # Get the message from command line arguments
        if len(sys.argv) < 2:
            result = {
                "response": "Error: No message provided",
                "success": False
            }
            print(json.dumps(result))
            return
        
        # The message is the first argument after the script name
        message = sys.argv[1]
        
        # Initialize the chatbot
        chatbot = CommunityWaterWatchChatbot()
        initialization_success = chatbot.initialize_pipeline()
        
        if not initialization_success:
            result = {
                "response": "Error: Failed to initialize the chatbot.",
                "success": False
            }
            print(json.dumps(result))
            return
        
        # Process the message
        response = chatbot.chat(message)
        
        # Clean the response by removing ANSI color codes
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_response = ansi_escape.sub('', response)
        
        # Return JSON response
        result = {
            "response": clean_response.strip(),
            "success": True
        }
        print(json.dumps(result))
        
    except Exception as e:
        # Return error response
        error_details = traceback.format_exc()
        result = {
            "response": f"An error occurred: {str(e)}",
            "success": False,
            "error_details": error_details
        }
        print(json.dumps(result))

if __name__ == "__main__":
    main()