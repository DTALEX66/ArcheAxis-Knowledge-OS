"""
AI Chat API for Xiaoqi virtual assistant
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    history: List[Message] = []


class ChatResponse(BaseModel):
    response: str
    state: str = "idle"


@router.post("/chat", response_model=ChatResponse)
async def chat_with_xiaoqi(request: ChatRequest):
    """
    小栖AI对话接口
    TODO: 集成实际的LLM（OpenAI/Anthropic/本地模型）
    """
    try:
        # 构建提示词
        context_prompt = f"\n相关上下文: {request.context}" if request.context else ""

        # 构建历史对话
        history_text = ""
        for msg in request.history[-5:]:  # 只取最近5条
            history_text += f"\n{msg.role}: {msg.content}"

        # TODO: 这里应该调用实际的LLM API
        # 示例：
        # response = await openai.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "你是小栖，ArcheAxis知识系统的AI助手。"},
        #         *[{"role": m.role, "content": m.content} for m in request.history],
        #         {"role": "user", "content": request.message}
        #     ]
        # )
        # ai_response = response.choices[0].message.content

        # 临时响应（模拟AI回复）
        if "学习" in request.message:
            ai_response = "我可以帮你制定学习计划，整理知识点，创建学习卡片。你想从哪里开始？"
        elif "复习" in request.message:
            ai_response = "根据你的学习进度，我建议先复习这些内容。要开始吗？"
        elif "知识" in request.message or "文档" in request.message:
            ai_response = f"关于{request.context or '这个主题'}，让我帮你查找相关的知识点..."
        else:
            ai_response = f"你提到了：{request.message}。我理解你的问题，让我来帮你分析一下。"

        return ChatResponse(
            response=ai_response,
            state="idle"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI对话失败: {str(e)}"
        )


@router.get("/status")
async def get_ai_status():
    """
    获取AI服务状态
    """
    return {
        "status": "online",
        "model": "simulated",  # TODO: 返回实际使用的模型
        "capabilities": ["chat", "knowledge", "learning"]
    }
