from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain
import json
import threading
import queue

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/research', methods=['POST'])
def research():
    data = request.get_json(force=True, silent=True) or {}
    topic = str(data.get('topic', '')).strip()

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    def generate():
        q = queue.Queue()

        def run_pipeline():
            try:
                state = {}

                # ── Step 1: Search Agent ──────────────────────────────
                q.put(('step', {
                    'step': 1,
                    'message': 'Search Agent: Scanning the web for relevant sources...'
                }))
                search_agent = build_search_agent()
                search_result = search_agent.invoke({
                    "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
                })
                state["search_results"] = search_result['messages'][-1].content

                # ── Step 2: Reader Agent ──────────────────────────────
                q.put(('step', {
                    'step': 2,
                    'message': 'Reader Agent: Scraping top URLs for deep content...'
                }))
                reader_agent = build_reader_agent()
                reader_result = reader_agent.invoke({
                    "messages": [("user",
                        f"Based on the following search results about '{topic}', "
                        f"pick the most relevant URL and scrape it for deeper content.\n\n"
                        f"Search Results:\n{state['search_results'][:800]}"
                    )]
                })
                state['scraped_content'] = reader_result['messages'][-1].content

                # ── Step 3: Writer Chain ──────────────────────────────
                q.put(('step', {
                    'step': 3,
                    'message': 'Writer: Crafting a professional research report...'
                }))
                research_combined = (
                    f"SEARCH RESULTS : \n {state['search_results']} \n\n"
                    f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
                )
                state["report"] = writer_chain.invoke({
                    "topic": topic,
                    "research": research_combined
                })

                # ── Step 4: Critic Chain ──────────────────────────────
                q.put(('step', {
                    'step': 4,
                    'message': 'Critic: Reviewing and scoring the report...'
                }))
                state["feedback"] = critic_chain.invoke({
                    "report": state['report']
                })

                q.put(('done', state))

            except Exception as e:
                import traceback
                q.put(('error', f"{str(e)}\n{traceback.format_exc()}"))

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        while True:
            try:
                item_type, item_data = q.get(timeout=180)

                if item_type == 'step':
                    yield f"data: {json.dumps({'type': 'step', 'data': item_data})}\n\n"

                elif item_type == 'done':
                    result = item_data
                    payload = {
                        'type': 'result',
                        'data': {
                            'search_results': str(result.get('search_results', '')),
                            'scraped_content': str(result.get('scraped_content', '')),
                            'report': str(result.get('report', '')),
                            'feedback': str(result.get('feedback', '')),
                        }
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    break

                elif item_type == 'error':
                    yield f"data: {json.dumps({'type': 'error', 'data': item_data})}\n\n"
                    break

            except queue.Empty:
                # Keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
