from llama_cpp import Llama


class LocalLLM:
    def __init__(self, config):
        self.config = config.model
        self.model = None
        self.chat_format = "auto"

    def load(self):
        self.model = Llama(
            model_path=self.config.path,
            n_ctx=self.config.n_ctx,
            n_threads=self.config.n_threads,
            n_gpu_layers=self.config.n_gpu_layers,
            n_batch=getattr(self.config, 'n_batch', 8),
            verbose=False,
        )

    def generate(self, prompt, max_tokens=512, temperature=0.1, stop=None):
        result = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop or [],
            echo=False,
        )
        return result["choices"][0]["text"].strip()

    def chat(self, messages, max_tokens=512, temperature=0.1):
        result = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return result["choices"][0]["message"]["content"].strip()

    def chat_stream(self, messages, max_tokens=512, temperature=0.1):
        stream = self.model.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                yield delta["content"]

    def unload(self):
        self.model = None
