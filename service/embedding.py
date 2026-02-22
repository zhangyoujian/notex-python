from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction,OpenAIEmbeddingFunction, OllamaEmbeddingFunction

class EmbeddingModel:
    def __init__(self, model_url: str, model_name: str, is_ollama: bool = False, api_key: str = "EMPTY"):
        self._is_ollama = is_ollama
        self._embedding_dim = None
        self._model_url = model_url
        self._model_name = model_name
        self._api_key = api_key

        self.model = self._create_embedding()

    def _create_embedding(self):
        if self._is_ollama: # 本地模型
            self._embedding_dim = 768
            return OllamaEmbeddingFunction(model_name=self._model_name, url=self._model_url)

        elif self._model_url != "": # 远程模型
            self._embedding_dim = 1024
            return OpenAIEmbeddingFunction(api_key=self._api_key, api_base=self._model_url, model_name=self._model_name)
        else: # 从云端下载模型
            model_ = SentenceTransformerEmbeddingFunction(model_name=self._model_name)
            self._embedding_dim = model_._get_model().get_sentence_embedding_dimension()
            return model_

    def get_embedding_model(self):
        return self.model

    def get_embedding_dim(self):
        return self._embedding_dim