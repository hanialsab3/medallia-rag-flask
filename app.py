from flask import Flask, request, jsonify
import os
import time
import requests

app = Flask(__name__)

# === CONFIGURE FROM ENVIRONMENT VARIABLES ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
API_BASE = "https://api.openai.com/v1"
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "assistants=v2",
    "Content-Type": "application/json"
}

@app.route("/ask-medallia", methods=["POST"])
def ask_medallia():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "Missing 'question' field."}), 400

    try:
        # Step 1: Create a thread
        resp = requests.post(f"{API_BASE}/threads", headers=HEADERS, json={})
        resp.raise_for_status()
        thread_id = resp.json().get("id")

        # Step 2: Add user message
        msg_payload = {"role": "user", "content": question}
        resp = requests.post(
            f"{API_BASE}/threads/{thread_id}/messages",
            headers=HEADERS,
            json=msg_payload
        )
        resp.raise_for_status()

        # Step 3: Run the assistant with file_search tool
        run_payload = {
            "assistant_id": ASSISTANT_ID,
            "tool_resources": {
                "file_search": {"vector_store_ids": [VECTOR_STORE_ID]}
            }
        }
        resp = requests.post(
            f"{API_BASE}/threads/{thread_id}/runs",
            headers=HEADERS,
            json=run_payload
        )
        resp.raise_for_status()
        run_id = resp.json().get("id")

        # Step 4: Poll for completion
        while True:
            resp = requests.get(
                f"{API_BASE}/threads/{thread_id}/runs/{run_id}",
                headers=HEADERS
            )
            resp.raise_for_status()
            status = resp.json().get("status")
            if status == "completed":
                break
            if status in ["failed", "cancelled"]:
                return jsonify({"error": f"Run {status}"}), 500
            time.sleep(1.5)

        # Step 5: Retrieve messages
        resp = requests.get(
            f"{API_BASE}/threads/{thread_id}/messages",
            headers=HEADERS
        )
        resp.raise_for_status()
        messages = resp.json().get("data", [])
        # Assume the last message is the assistant's reply
        if not messages:
            return jsonify({"error": "No messages found."}), 500
        last = messages[-1]
        # Extract the text value
        answer = last.get("content", [])[0].get("text", {}).get("value")

        return jsonify({"answer": answer})

    except requests.HTTPError as e:
        return jsonify({"error": e.response.text}), e.response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
