from flask import Flask, request, jsonify
import openai
import time
import os

app = Flask(__name__)

# === CONFIGURE FROM ENVIRONMENT VARIABLES ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

openai.api_key = OPENAI_API_KEY

@app.route("/ask-medallia", methods=["POST"])
def ask_medallia():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "Missing 'question' field."}), 400

    try:
        # Step 1: Create a thread
        thread = openai.beta.threads.create()

        # Step 2: Add user message
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )

        # Step 3: Run the assistant with file_search
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            tool_resources={
                "file_search": {
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            }
        )

        # Step 4: Poll for completion
        while True:
            status = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            ).status

            if status == "completed":
                break
            elif status in ["failed", "cancelled"]:
                return jsonify({"error": f"Run {status}"}), 500

            time.sleep(1.5)

        # Step 5: Retrieve messages
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        response_text = messages.data[0].content[0].text.value

        return jsonify({"answer": response_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
