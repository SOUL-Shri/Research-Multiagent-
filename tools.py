from langchain.tools import tool 
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os 
from dotenv import load_dotenv
from rich import print
load_dotenv()

tavily=TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def web_search(query: str) -> str:
    """Search the recent and reliable information on a topic . Returns Titles URL and snnipet. """
    results=tavily.search(query=query,max_result=3)
    
    out=[]
    for r in results['results']:
        out.append(f"Title: {r['title']}\nURL: {r['url']}\nSnnipet: {r['content'][:300]}\n")


    return "\n----------\n".join(out)

#web_search.invoke("what are the recent news of AI?")
#print(web_search.invoke("what are the recent news of AI?"))
@tool
def scrape_url(url: str) -> str:
    """Scrape the content of a URL and return the text whcih is clean and better for deep learning model. """
    try:
        resp = requests.get(url,timeout = 5 , headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'})
        resp.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(resp.text, 'html.parser')
        for tag in soup(['script', 'style','nav','header','footer','aside']):  # Add more tags to remove if needed
            tag.decompose()  # Remove script and style elements
        return soup.get_text(separator=" ", strip=True)[:3000]
    except requests.RequestException as e:
        return f"An error occurred while trying to scrape the URL: {str(e)}"
    