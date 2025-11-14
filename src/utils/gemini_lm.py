from google import genai
import dspy


class FakeUsage:
    def __init__(self, prompt_tokens=0, completion_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
    
    def __iter__(self):
        """Make FakeUsage iterable for dict() conversion"""
        yield ('prompt_tokens', self.prompt_tokens)
        yield ('completion_tokens', self.completion_tokens)
        yield ('total_tokens', self.total_tokens)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content, prompt_tokens=0, completion_tokens=0, model="gemini"):
        self.choices = [FakeChoice(content)]
        self.usage = FakeUsage(prompt_tokens, completion_tokens)
        self.model = model


class GeminiLM(dspy.LM):
    def __init__(self, model, api_key):
        super().__init__(model="custom_gemini")

        self.model_name = model
        self.client = genai.Client(api_key=api_key)
        self.use_litellm = False

    def forward(self, prompt=None, messages=None, **kwargs):
        # extract prompt string DSPy sends
        if messages:
            contents = "\n".join(
                m["content"] for m in messages if m.get("role") == "user"
            )
        else:
            contents = prompt

        # call Gemini SDK
        gemini_response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        # get response text
        text = gemini_response.text

        # estimate tokens (Gemini doesn't give usage)
        prompt_tokens = len(contents) // 4
        completion_tokens = len(text) // 4

        # return LiteLLM-compatible structured object
        return FakeResponse(
            content=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model_name,
        )

