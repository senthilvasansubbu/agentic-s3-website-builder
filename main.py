#!/usr/bin/env python3
"""
Agentic AI Website Builder - Main Application Entry Point

This application uses a multi-agent system (CrewAI) with OpenAI GPT-4
to create beautiful, responsive websites based on conversational user input.
"""

import os
import sys
from datetime import datetime
from config.settings import settings
from agents.crew import build_website
from tools.html_generator import generate_html, create_index_html
from tools.s3_uploader import uploader

def display_welcome():
    """Display welcome message and instructions"""
    print("\n" + "="*70)
    print("🚀 Welcome to Agentic AI Website Builder")
    print("="*70)
    print("\nDescribe the website you want to create, and our AI agents will:")
    print("  1. 🎨 Design the visual layout and style")
    print("  2. 💻 Generate the HTML/CSS/JavaScript code")
    print("  3. 📁 Save it to the 'output' folder")
    print("  4. ☁️  Optionally upload to S3 (if configured)")
    print("\nType 'exit' or 'quit' to stop the application.")
    print("Type 'help' for more information.")
    print("="*70 + "\n")

def display_help():
    """Display help information"""
    print("\n" + "-"*70)
    print("📚 Help Information")
    print("-"*70)
    print("""
Examples of website descriptions you can use:

1. "Create a modern portfolio website for a photographer with a gallery, 
   about page, and contact form"

2. "Build a landing page for a tech startup with dark theme, pricing table,
   and feature highlights"

3. "Design a blog website with a sidebar, navigation menu, and article cards"

4. "Create a restaurant website with menu display, reservation form, and 
   location information"

5. "Build an e-commerce product page with image gallery, reviews, and 
   add to cart button"

Tips:
- Be descriptive about colors, layout, and functionality
- Mention specific sections or components you want
- Specify the target audience or purpose
- Describe the overall style/theme (minimalist, bold, professional, etc.)

The AI will generate a complete, ready-to-use website based on your description.
""")
    print("-"*70 + "\n")

def validate_requirements(requirements: str) -> bool:
    """Validate user requirements"""
    if not requirements or len(requirements.strip()) < 10:
        print("❌ Please provide a more detailed description (at least 10 characters)")
        return False
    return True

def process_website_request(user_input: str) -> bool:
    """
    Process a website creation request
    
    Args:
        user_input: User's website description
        
    Returns:
        True if successful, False otherwise
    """
    if not validate_requirements(user_input):
        return False
    
    try:
        print("\n🤖 Starting website creation process...\n")
        
        # Build website using crew
        result = build_website(user_input)
        
        if result["status"] == "success":
            # Extract the result — fallback returns a plain string; CrewAI returns an object
            raw = result.get("result", "")
            html_code = raw if isinstance(raw, str) else str(raw)
            
            if not html_code:
                print("❌ Failed to generate website code")
                return False
            
            # Generate HTML file
            project_name = user_input.split()[0:3]
            project_name = "_".join(project_name).replace(" ", "_")
            filepath = generate_html({}, html_code, project_name)
            
            print(f"\n✅ Website created successfully!")
            print(f"📁 File saved to: {filepath}")
            
            # Try to upload to S3
            s3_url = uploader.upload_file(filepath)
            if s3_url:
                print(f"☁️  S3 URL: {s3_url}")
            
            return True
        else:
            print("❌ Failed to create website")
            return False
    
    except Exception as e:
        print(f"❌ Error during website creation: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main application loop"""
    try:
        # Validate settings
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please set up your environment variables. See .env.example for details.")
        sys.exit(1)
    
    display_welcome()
    
    websites_created = []
    
    while True:
        try:
            # Get user input
            user_input = input("📝 Describe your website (or type 'help'/'exit'): ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Thank you for using Agentic AI Website Builder!")
                print(f"📊 Websites created this session: {len(websites_created)}")
                if websites_created:
                    print("📂 Check the 'output' folder for your generated websites")
                break
            
            if user_input.lower() == 'help':
                display_help()
                continue
            
            if user_input.lower() == 'list':
                if websites_created:
                    print("\n📋 Websites created this session:")
                    for i, website in enumerate(websites_created, 1):
                        print(f"  {i}. {website}")
                else:
                    print("\n📋 No websites created yet this session")
                continue
            
            # Process website request
            if process_website_request(user_input):
                websites_created.append(user_input[:50])
                print("\n" + "-"*70 + "\n")
            else:
                print("\n⚠️  Please try again with a different description.\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Application interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            print("Please try again.\n")

if __name__ == "__main__":
    main()
