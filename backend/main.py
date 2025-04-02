from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from jinja2 import Template
from typing import List
import os

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda

from langchain_core.tracers.context import tracing_v2_enabled
from langchain.schema import HumanMessage

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Load Ollama LLM with deterministic output
llm = ChatOllama(
    model="gemma3:4b",
    default_ollama_options={"temperature": 0.7}
)

# === Request model ===
class ChatRequest(BaseModel):
    user_message: str
    tone: str  # "friendly", "motivational", "sarcastic", etc.

class BatchChatRequest(BaseModel):
    prompts: List[ChatRequest]

# === Load prompt template ===
with open("templates/base_prompt.jinja2") as f:
    base_template = Template(f.read())

def render_prompt(user_message: str, tone: str) -> str:
    return base_template.render(user_message=user_message, tone=tone)

# === Async + Streaming endpoint ===
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    rendered_prompt = render_prompt(req.user_message, req.tone)

    full_chain = (
        RunnableLambda(lambda x: [
            SystemMessage("Be concise and direct."),
            HumanMessage(content=x)
        ]) | llm
    )

    async def token_stream():
        with tracing_v2_enabled(project_name="Gym Assistant"):
            async for chunk in full_chain.astream(rendered_prompt):
                yield chunk.content or ""

    return StreamingResponse(token_stream(), media_type="text/plain")


# === Batch endpoint ===
@app.post("/chat/batch")
async def chat_batch(req: BatchChatRequest):
    prompts = [render_prompt(p.user_message, p.tone) for p in req.prompts]

    chain = RunnableLambda(lambda x: [
        SystemMessage("Be concise and direct."),
        HumanMessage(content=x)
    ]) | llm

    with tracing_v2_enabled(project_name="Gym Assistant"):
        results = await chain.abatch(prompts)

    return {
        "responses": [res.content for res in results]
    }