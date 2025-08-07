from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.browserbase import BrowserbaseTools

# Note: Enhanced BrowserbaseTools with 10-minute timeouts for slow government pages

# Create an advanced sales research agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools(), BrowserbaseTools()],
    instructions="""You are an Advanced Sales Research Agent for the alcohol industry.

    Your goal: Conduct comprehensive supplier research with detailed COLA registry analysis.

    ## Advanced COLA Registry Workflow:

     ### Step 1: Initial Search
     - Navigate to: https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do
     - Fill search form with date range (last 1-2 months) and company name
     - Use CSS selectors (with extended 10-minute timeouts for slow-loading pages):
       * input[name="searchCriteria.dateCompletedFrom"] (MM/DD/YYYY)
       * input[name="searchCriteria.dateCompletedTo"] (MM/DD/YYYY)
       * input[name="searchCriteria.productOrFancifulName"] (brand name)
     - Submit with: input[type="submit"]
     - After submission, results appear on: https://ttbonline.gov/colasonline/publicSearchColasBasicProcess.do?action=search

     ### Step 2: Results Analysis
     - On the results page (publicSearchColasBasicProcess.do?action=search)
     - Take screenshot of search results
     - Extract ALL result links from the results table
     - Count total COLA approvals found

    ### Step 3: Individual Record Analysis (CRITICAL)
    - Click on EACH individual result link to open detailed COLA records
    - For each COLA record, extract complete details:
      * TTB ID and approval date
      * Product type and alcohol content
      * Brand and fanciful names
      * Permit holder information
      * Label images and descriptions
      * Geographic origin
    - Take screenshots of each detailed record
    - Navigate back to results for next record

    ### Step 4: Comprehensive Analysis
    - Compile data from ALL individual COLA records
    - Identify approval patterns and trends
    - Analyze product portfolio breadth
    - Assess regulatory compliance

     Generate detailed report with executive summary, complete COLA portfolio analysis, 
     and strategic recommendations. Be thorough - examine every single COLA record found.
     
     IMPORTANT: If CSS selectors fail, try alternative approaches:
     - Take screenshot first to see form structure
     - Try alternative selectors like [name="searchCriteria.dateCompletedFrom"] (without input prefix)
     - Use get_page_content to examine HTML structure if needed""",
    markdown=True,
    # show_tool_calls=True,
    debug_mode=True,
)

# Research a supplier with comprehensive COLA analysis
def research_supplier(company_name: str):
    """Research a supplier with detailed COLA registry analysis."""
    prompt = f"""Conduct comprehensive research on "{company_name}" as a potential alcohol industry supplier.

    Execute the full Advanced COLA Registry Workflow:

    1. **Company Research**: Use web search to find background, leadership, business model

     2. **COLA Registry Deep Dive**: 
        - Navigate to TTB COLA registry (https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do)
        - Fill search form using EXACT CSS selectors:
          * input[name="searchCriteria.dateCompletedFrom"] with recent date (e.g., "10/01/2024")
          * input[name="searchCriteria.dateCompletedTo"] with current date (e.g., "12/31/2024")  
          * input[name="searchCriteria.productOrFancifulName"] with "{company_name}"
        - Use date range: last 2 months for comprehensive analysis
        - Submit form with: input[type="submit"]
        - After submitting search, results will appear on: https://ttbonline.gov/colasonline/publicSearchColasBasicProcess.do?action=search
        - Take screenshot of search results page
        - Click on EVERY individual COLA result link from the results table
        - Extract complete details from each COLA record
        - Take screenshots of each detailed record
        - Navigate back to results page for next record
        - Compile comprehensive portfolio analysis

    3. **Analysis & Report**: Generate detailed report with:
       - Executive summary with clear recommendation
       - Complete COLA portfolio analysis (every approval found)
       - Product category breakdown and trends
       - Approval timing patterns
       - Regulatory compliance assessment
       - Strategic recommendations with priority actions

    Be extremely thorough - examine every single COLA record found. This is critical market intelligence."""

    return agent.print_response(prompt)

# Example usage
if __name__ == "__main__":
    # Research a well-known alcohol industry supplier
    company_name = "Sazerac Company"
    
    print(f"🍷 Researching: {company_name}")
    print("🔍 Performing comprehensive supplier analysis with detailed COLA registry examination")
    print("⚠️  This will examine every individual COLA record found - may take several minutes")
    print("⏱️  Enhanced with 10-minute timeouts for slow-loading government pages")
    print("-" * 80)
    
    research_supplier(company_name)