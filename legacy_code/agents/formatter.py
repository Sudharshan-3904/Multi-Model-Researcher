class Formatter:
    def format(self, analysis, chat_title, topic, provider, model):
        # Simple formatting for demonstration
        report = f"# {chat_title}\n\n**Topic:** {topic}\n**Provider:** {provider}\n**Model:** {model}\n\n---\n\n{analysis}"
        return report
