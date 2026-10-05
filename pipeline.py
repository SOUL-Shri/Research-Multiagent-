import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain, extract_text_from_message
import time

def run_research_pipeline(topic: str) -> dict:

    state = {}

    # step 1 - search agent 
    print("\n" + " =" * 50)
    print("step 1 - search agent is working ...")
    print("=" * 50)

    search_agent = build_search_agent()
    t0 = time.monotonic()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
    })
    search_time = time.monotonic() - t0
    print(f"Search took {search_time:.2f} s")
    state["search_results"] = extract_text_from_message(search_result['messages'][-1])

    print("\n search result:\n", state['search_results'])

    # step 2 - reader agent 
    print("\n" + " =" * 50)
    print("step 2 - Reader agent is scraping top resources ...")
    print("=" * 50)

    reader_agent = build_reader_agent()
    t0 = time.monotonic()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_results'][:3000]}"
        )]
    })
    reader_time = time.monotonic() - t0
    print(f"Reader (scrape) took {reader_time:.2f} s")

    state['scraped_content'] = extract_text_from_message(reader_result['messages'][-1])

    print("\n scraped content:\n", state['scraped_content'])

    # step 3 - writer chain 
    print("\n" + " =" * 50)
    print("step 3 - Writer is drafting the report ...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{state['scraped_content']}"
    )

    t0 = time.monotonic()
    writer_res = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })
    writer_time = time.monotonic() - t0
    state["report"] = extract_text_from_message(writer_res)
    print(f"Writer took {writer_time:.2f} s")

    print("\n Final Report:\n", state.get('report'))

    # step 4 - critic report 
    print("\n" + " =" * 50)
    print("step 4 - critic is reviewing the report ")
    print("=" * 50)

    t0 = time.monotonic()
    critic_res = critic_chain.invoke({
        "report": state['report']
    })
    critic_time = time.monotonic() - t0
    state["feedback"] = extract_text_from_message(critic_res)
    print(f"Critic took {critic_time:.2f} s")

    print("\n critic report:\n", state['feedback'])

    return state


if __name__ == "__main__":
    topic = input("\n Enter a research topic: ")
    run_research_pipeline(topic)
