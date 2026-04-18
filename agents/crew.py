from crewai import Crew, Process, Task
from agents.designer_agent import designer_agent
from agents.developer_agent import developer_agent
from config.settings import settings


def _generate_static_fallback(user_requirements: str) -> str:
    """Generate a basic static HTML website when no API key is available."""
    title = " ".join(user_requirements.split()[:6]).title()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; }}
    header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 60px 20px; text-align: center; }}
    header h1 {{ font-size: 2.5rem; margin-bottom: 12px; }}
    header p {{ font-size: 1.1rem; opacity: 0.9; max-width: 600px; margin: 0 auto; }}
    nav {{ background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.08); display: flex; justify-content: center; gap: 32px; padding: 16px; }}
    nav a {{ text-decoration: none; color: #667eea; font-weight: 600; transition: color .2s; }}
    nav a:hover {{ color: #764ba2; }}
    main {{ max-width: 1100px; margin: 48px auto; padding: 0 20px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; margin-top: 32px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 28px; box-shadow: 0 4px 16px rgba(0,0,0,.07); transition: transform .2s; }}
    .card:hover {{ transform: translateY(-4px); }}
    .card h3 {{ color: #667eea; margin-bottom: 10px; }}
    .btn {{ display: inline-block; margin-top: 40px; padding: 14px 36px; background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; border-radius: 8px; text-decoration: none; font-weight: 700; transition: opacity .2s; }}
    .btn:hover {{ opacity: .88; }}
    footer {{ text-align: center; padding: 32px; background: #fff; margin-top: 60px; color: #888; font-size: .9rem; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>{user_requirements}</p>
  </header>
  <nav>
    <a href="#home">Home</a>
    <a href="#about">About</a>
    <a href="#services">Services</a>
    <a href="#contact">Contact</a>
  </nav>
  <main>
    <h2>Welcome</h2>
    <p>This website was generated based on your requirements. Add your content below.</p>
    <div class="cards">
      <div class="card"><h3>Feature One</h3><p>Describe your first feature or section here.</p></div>
      <div class="card"><h3>Feature Two</h3><p>Describe your second feature or section here.</p></div>
      <div class="card"><h3>Feature Three</h3><p>Describe your third feature or section here.</p></div>
    </div>
    <a class="btn" href="#contact">Get Started</a>
  </main>
  <footer>&copy; 2026 {title}. All rights reserved.</footer>
</body>
</html>"""


def create_website_crew():
    """Create and configure the website builder crew"""
    
    # Task 1: Design specifications
    design_task = Task(
        description="""Based on the user's requirements, create a detailed design specification including:
        1. Layout structure and wireframe description
        2. Color scheme (primary, secondary, accent colors with hex codes)
        3. Typography (font families, sizes, weights for different elements)
        4. Component styles (buttons, cards, navigation, etc.)
        5. Responsive breakpoints strategy
        6. Special design elements or animations
        
        Provide the output in a structured format that the developer can use.""",
        agent=designer_agent,
        expected_output="Detailed design specifications with colors, typography, layout, and styling guidelines"
    )
    
    # Task 2: Code generation
    code_task = Task(
        description="""Based on the design specifications from the designer, generate a complete, 
        production-ready HTML/CSS/JavaScript website. 
        
        Requirements:
        1. Write complete, valid HTML5 code
        2. Include responsive CSS using Grid and Flexbox
        3. Add interactive features with vanilla JavaScript
        4. Ensure semantic HTML structure
        5. Optimize for performance
        6. Include proper meta tags for SEO
        7. Make it mobile-friendly
        
        Provide the complete code as a single HTML file that can be opened in a browser.""",
        agent=developer_agent,
        expected_output="Complete HTML file with embedded CSS and JavaScript ready to be deployed"
    )
    
    crew = Crew(
        agents=[designer_agent, developer_agent],
        tasks=[design_task, code_task],
        process=Process.sequential,
        verbose=settings.VERBOSE_MODE
    )
    
    return crew

def build_website(user_requirements: str) -> dict:
    """
    Build a website based on user requirements.
    Falls back to a static template when OPENAI_API_KEY is not configured.
    """
    if not settings.OPENAI_API_KEY:
        print("⚠️  No OPENAI_API_KEY found — generating static template website instead.")
        html_code = _generate_static_fallback(user_requirements)
        return {
            "status": "success",
            "result": html_code,
            "requirements": user_requirements,
            "fallback": True,
        }

    crew = create_website_crew()
    
    result = crew.kickoff(
        inputs={
            "user_requirements": user_requirements,
            "project_name": user_requirements.split()[0] if user_requirements else "Website"
        }
    )
    
    return {
        "status": "success",
        "result": result,
        "requirements": user_requirements
    }
