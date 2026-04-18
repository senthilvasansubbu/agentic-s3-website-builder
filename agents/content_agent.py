"""
Content research CrewAI agent.
Searches the web and social media to gather relevant content for a website topic.
"""
from crewai import Agent, LLM
from config.settings import settings

llm = LLM(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)

content_researcher_agent = Agent(
    role="Content Researcher",
    goal=(
        "Research a given website topic using real-world web and social-media data, "
        "then produce well-structured, accurate page content (headings, paragraphs, "
        "bullet points, calls-to-action) that can be directly embedded in HTML."
    ),
    backstory="""You are an expert digital content strategist and researcher with 10+ years
    of experience building high-converting website copy.  You combine live web search results,
    social-media trends, and SEO best practices to produce compelling, factually-grounded
    content for any industry.  You always cite your sources and avoid hallucination.""",
    verbose=settings.VERBOSE_MODE,
    allow_delegation=False,
    llm=llm,
)
