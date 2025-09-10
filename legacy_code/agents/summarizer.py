import asyncio

class Summarizer:
    def __init__(self, model_interface, model_name, model_provider):
        self.model_interface = model_interface
        self.model_name = model_name
        self.model_provider = model_provider

    async def summarize_article(self, article_text, query):
        prompt = f"Summarize the following article in a short paragraph for the query: '{query}'.\n\nArticle:\n{article_text}"
        return await self.model_interface.summarize(prompt, model_name=self.model_name, model_provider=self.model_provider)

    async def summarize_all(self, articles, query):
        async def summarize_one(article):
            title = article.get('title', 'No Title')
            citations = article.get('citations', 0)
            abstract = article.get('abstract', '')
            text = article.get('text', '')
            full_text = f"Abstract: {abstract}\n\n{text}"
            summary = await self.summarize_article(full_text, query)
            return f"- {title} (Citations: {citations})\n{summary}"

        return await asyncio.gather(*(summarize_one(article) for article in articles))

