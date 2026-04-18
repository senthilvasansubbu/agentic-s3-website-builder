from crewai import Agent, LLM
from config.settings import settings

# Initialize the LLM
llm = LLM(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)

designer_agent = Agent(
    role="UI/UX Designer",
    goal="Create visually appealing and user-friendly website designs based on user requirements",
    backstory="""You are an expert UI/UX designer with 15+ years of experience creating beautiful, 
    responsive websites. You understand modern design principles, color theory, typography, and 
    user experience best practices. You create detailed design specifications including layout, 
    color schemes, typography, and component styles.""",
    verbose=settings.VERBOSE_MODE,
    allow_delegation=False,
    llm=llm
)
