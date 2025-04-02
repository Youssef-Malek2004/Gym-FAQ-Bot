import streamlit as st
import requests
import re

st.set_page_config(page_title="Gym Assistant", layout="wide")

API_BASE = "http://localhost:8000"

# === UTIL: Clean + format streamed markdown ===
def format_response(raw: str) -> str:
    raw = raw.replace("*", "**")  # ensure * turns into bold
    raw = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", raw)  # bold
    raw = re.sub(r"### (.*?)\n", r"<h4>\1</h4>", raw)  # h4 headings
    raw = raw.replace("\n", "<br>")  # line breaks
    return raw.strip()

# === PAGE SELECTOR ===
page = st.sidebar.selectbox("Choose a page", ["🧠 Live Chat", "📦 Batch Chat"])

# === PAGE 1: Streamed Chat ===
if page == "🧠 Live Chat":
    st.title("🏋️‍♂️ Gym Assistant - Live Chat")

    # Inputs
    user_input = st.text_input("Ask me anything about fitness 🏋️")
    tone = st.selectbox("Choose a tone", ["friendly", "motivational", "sarcastic", "formal", "casual"])

    if st.button("💬 Ask"):
        if not user_input:
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Thinking..."):
                response = requests.post(
                    f"{API_BASE}/chat/stream",
                    json={"user_message": user_input, "tone": tone},
                    stream=True
                )

                placeholder = st.empty()
                full_response = ""

                for chunk in response.iter_lines():
                    if chunk:
                        piece = chunk.decode("utf-8")
                        full_response += piece
                        html_block = f"""
                        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; font-size: 16px;">
                            <strong>🏋️ Response:</strong><br><br>
                            {format_response(full_response)}
                        </div>
                        """
                        placeholder.markdown(html_block, unsafe_allow_html=True)

# === PAGE 2: Batch ===
elif page == "📦 Batch Chat":
    st.title("📦 Gym Assistant - Batch Questions")

    with st.form("batch_form"):
        st.write("Add multiple fitness questions and choose a tone for each:")
        batch_questions = st.text_area("Format: question | tone", height=200,
            placeholder="e.g.\nWhat is the best warm-up? | friendly\nWhat should I eat post-workout? | motivational")
        submit = st.form_submit_button("🚀 Submit Batch")

    if submit:
        if not batch_questions.strip():
            st.warning("Please enter at least one question.")
        else:
            prompt_lines = batch_questions.strip().split("\n")
            prompts = []

            for line in prompt_lines:
                if "|" in line:
                    q, t = line.split("|", 1)
                    prompts.append({"user_message": q.strip(), "tone": t.strip()})
                else:
                    st.error(f"Invalid format: {line}")

            with st.spinner("Processing..."):
                res = requests.post(f"{API_BASE}/chat/batch", json={"prompts": prompts})
                responses = res.json().get("responses", [])

            for i, (p, r) in enumerate(zip(prompts, responses)):
                st.markdown(f"**Q{i+1}:** *{p['user_message']}* _(tone: {p['tone']})_")
                st.success(r)
