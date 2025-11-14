from google import genai
import dspy


class GeminiLM(dspy.LM):
    def __init__(self, model, api_key):
        # DSPy needs a model argument here, even though we override internally
        super().__init__(model=model)

        self.model_name = model
        self.client = genai.Client(api_key=api_key)

        # Disable LiteLLM entirely
        self.use_litellm = False

        # Prevent DSPy from sending any model name to LiteLLM
        self.model = None

    def forward(self, prompt=None, messages=None, **kwargs):
        # Convert messages → text (DSPy format)
        if messages:
            contents = "\n".join(
                m["content"] for m in messages if m.get("role") == "user"
            )
        else:
            contents = prompt

        # Call Google Gemini (official SDK)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        # Return DSPy-style ChatCompletion format
        return {
            "choices": [{
                "message": {
                    "content": response.text
                }
            }]
        }
