import os
import sys
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv
from langchain.tools import tool

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

tavily_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=tavily_key) if tavily_key else None

@tool
def web_search(query: str) -> str:
    """Search the recent and reliable information on a topic. Returns Titles, URLs and snippets."""
    if not tavily:
        return "Error: TAVILY_API_KEY is not configured in .env file."
    try:
        results = tavily.search(query=query, max_results=3)
        out = []
        for r in results.get('results', []):
            title = r.get('title', 'No Title')
            url = r.get('url', '')
            content = r.get('content', '')[:400]
            out.append(f"Title: {title}\nURL: {url}\nSnippet: {content}\n")
        return "\n----------\n".join(out) if out else "No web search results found."
    except Exception as e:
        return f"Error executing web search: {str(e)}"

@tool
def scrape_url(url: str) -> str:
    """Scrape the content of a URL and return clean text."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resp = requests.get(url, timeout=8, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:4000] if text else "No readable text content found on the page."
    except requests.RequestException as e:
        return f"An error occurred while trying to scrape the URL: {str(e)}"