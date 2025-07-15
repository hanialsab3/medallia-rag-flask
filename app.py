from flask import Flask, request, jsonify
import openai
import time

app = Flask(__name__)

# === CONFIGURE THESE ===
OPENAI_API_KEY = "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"
ASSISTANT_ID = "asst_EvYj7VGar4KpNBv2KyPVIab0"
VECTOR_STORE_ID = "vs_68739df5ea6081919a0de82666775055"

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
    app.run(debug=True)
