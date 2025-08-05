"""Article summarization using LLMs."""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
# Optional httpx import
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None
from .models import Article, Summary, ArticleStatus


class Summarizer:
    """Base class for article summarization."""
    
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name
    
    async def summarize(self, article: Article) -> Optional[Summary]:
        """Summarize an article."""
        raise NotImplementedError


class OllamaSummarizer(Summarizer):
    """Summarizer using Ollama local LLM."""
    
    def __init__(self, model_name: str = "llama2", base_url: str = "http://localhost:11434"):
        super().__init__(model_name)
        self.base_url = base_url.rstrip("/")
        if HTTPX_AVAILABLE:
            self.client = httpx.AsyncClient(timeout=60)
        else:
            self.client = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client and HTTPX_AVAILABLE:
            await self.client.aclose()
    
    async def summarize(self, article: Article) -> Optional[Summary]:
        """Generate a summary using Ollama."""
        if not article.cleaned_content or not HTTPX_AVAILABLE:
            return None
        
        # Prepare the prompt
        prompt = self._create_summary_prompt(article)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            response.raise_for_status()
            
            result = response.json()
            summary_text = result.get("response", "").strip()
            
            if not summary_text:
                return None
            
            return Summary(
                article_id=article.id,
                content=summary_text,
                model_used=f"ollama:{self.model_name}",
                tokens_used=result.get("eval_count", 0)
            )
            
        except Exception as e:
            print(f"Error summarizing article {article.id}: {e}")
            return None
    
    def _create_summary_prompt(self, article: Article) -> str:
        """Create a prompt for summarization."""
        return f"""Please provide a concise summary of the following article in 2-3 sentences:

Title: {article.title}
Author: {article.author or 'Unknown'}

Content:
{article.cleaned_content[:2000]}

Summary:"""


class OpenAISummarizer(Summarizer):
    """Summarizer using OpenAI API."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo"):
        super().__init__(model_name)
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client and HTTPX_AVAILABLE:
            await self.client.aclose()
    
    async def summarize(self, article: Article) -> Optional[Summary]:
        """Generate a summary using OpenAI."""
        if not article.cleaned_content or not HTTPX_AVAILABLE:
            return None
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that creates concise, informative summaries of articles."
                        },
                        {
                            "role": "user",
                            "content": f"Please provide a 2-3 sentence summary of this article:\n\nTitle: {article.title}\n\nContent: {article.cleaned_content[:2000]}"
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            
            result = response.json()
            summary_text = result["choices"][0]["message"]["content"].strip()
            
            return Summary(
                article_id=article.id,
                content=summary_text,
                model_used=f"openai:{self.model_name}",
                tokens_used=result["usage"]["total_tokens"]
            )
            
        except Exception as e:
            print(f"Error summarizing article {article.id}: {e}")
            return None


class MockSummarizer(Summarizer):
    """Mock summarizer for testing."""
    
    async def summarize(self, article: Article) -> Optional[Summary]:
        """Generate a mock summary."""
        if not article.cleaned_content:
            return None
        
        # Create a simple summary based on the first few sentences
        sentences = article.cleaned_content.split('.')[:3]
        summary = '. '.join(sentences) + '.'
        
        return Summary(
            article_id=article.id,
            content=summary,
            model_used="mock",
            tokens_used=len(summary.split())
        )


class SummarizerFactory:
    """Factory for creating summarizers."""
    
    @staticmethod
    def create_summarizer(
        summarizer_type: str = "ollama",
        model_name: str = "llama2",
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434"
    ) -> Summarizer:
        """Create a summarizer based on type."""
        if summarizer_type == "ollama":
            return OllamaSummarizer(model_name, base_url)
        elif summarizer_type == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAISummarizer(api_key, model_name)
        elif summarizer_type == "mock":
            return MockSummarizer(model_name)
        else:
            raise ValueError(f"Unknown summarizer type: {summarizer_type}")


class BatchSummarizer:
    """Handles batch summarization of articles."""
    
    def __init__(self, summarizer: Summarizer, max_concurrent: int = 5):
        self.summarizer = summarizer
        self.max_concurrent = max_concurrent
    
    async def summarize_batch(self, articles: List[Article]) -> List[Summary]:
        """Summarize a batch of articles concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def summarize_with_semaphore(article: Article) -> Optional[Summary]:
            async with semaphore:
                async with self.summarizer:
                    return await self.summarizer.summarize(article)
        
        tasks = [summarize_with_semaphore(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        summaries = []
        for result in results:
            if isinstance(result, Summary):
                summaries.append(result)
            elif isinstance(result, Exception):
                print(f"Error in batch summarization: {result}")
        
        return summaries