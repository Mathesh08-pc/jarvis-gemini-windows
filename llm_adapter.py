import base64
import logging
import google.generativeai as genai

log = logging.getLogger("jarvis.adapter")

class MockMessage:
    def __init__(self, text: str):
        self.text = text

class MockContent:
    def __init__(self, text: str):
        self.content = [MockMessage(text)]

class MockUsage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

class MockMessagesResponse:
    def __init__(self, text: str, in_t: int, out_t: int):
        self.content = [MockMessage(text)]
        self.usage = MockUsage(in_t, out_t)

class GeminiMessagesAPI:
    def __init__(self, model_name: str):
        self.model_name = model_name

    async def create(self, model=None, max_tokens=1024, messages=None, system=None, **kwargs):
        if messages is None:
            messages = []
            
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            content = msg["content"]
            
            if isinstance(content, str):
                gemini_messages.append({"role": role, "parts": [content]})
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append(block["text"])
                    elif block.get("type") == "image":
                        mime_type = block["source"]["media_type"]
                        b64_data = block["source"]["data"]
                        parts.append({"mime_type": mime_type, "data": base64.b64decode(b64_data)})
                gemini_messages.append({"role": role, "parts": parts})
                
        # To avoid system prompt injection errors when gemini expects user first
        # we can pass it via system_instruction
        try:
            genai_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system
            )
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7
            )
            
            response = await genai_model.generate_content_async(
                gemini_messages, 
                generation_config=generation_config
            )
            
            # Simple token approximation if metadata missing
            in_t = getattr(response.usage_metadata, "prompt_token_count", 0) if hasattr(response, "usage_metadata") else len(str(messages)) // 4
            out_t = getattr(response.usage_metadata, "candidates_token_count", 0) if hasattr(response, "usage_metadata") else len(response.text) // 4
            
            return MockMessagesResponse(response.text, in_t, out_t)
        except Exception as e:
            log.error(f"Gemini error: {e}")
            return MockMessagesResponse("Apologies, I encountered an error connecting to my core processing unit.", 0, 0)

class GeminiAdapter:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.messages = GeminiMessagesAPI("gemini-1.5-pro")

# Mock types for type hints
AsyncAnthropic = GeminiAdapter
