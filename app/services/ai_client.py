"""
AI Client
Handles communication with AI services like Ollama.
"""

import json
import requests
import threading
from typing import Dict, Any, Callable

class OllamaClient:
    """Client for interacting with the Ollama API."""

    def __init__(self, host: str = "http://localhost:11434"):
        """Initialize the client with a specific model."""
        self.host = host
        self.api_url = f"{self.host}/api/generate"
        self.stop_event = threading.Event()

    def get_explanation(self, model: str, sentence: str, context: str, on_chunk: Callable[[str], None], on_done: Callable[[], None], study_mode: bool = False, user_prompt: str = None):
        """Get an explanation for a sentence within a given context."""
        self.stop_event.clear()
        thread = threading.Thread(
            target=self._stream_explanation,
            args=(model, sentence, context, on_chunk, on_done, study_mode, user_prompt)
        )
        thread.start()

    def _create_prompt(self, sentence: str, context: str, study_mode: bool = False, user_prompt: str = None) -> str:
        """Create a detailed prompt for the Ollama model."""
        from app.utils.translation_manager import get_translation_manager
        tm = get_translation_manager()
        
        if study_mode:
            return self._create_study_mode_prompt(sentence, context, tm, user_prompt)
        else:
            return self._create_regular_prompt(sentence, context, tm, user_prompt)
    
    def _create_regular_prompt(self, sentence: str, context: str, tm, user_prompt: str = None) -> str:
        """Create regular mode prompt."""
        context_intro = tm.translate("ai.prompts.context_intro")
        
        # Use user_prompt if provided, otherwise use sentence
        target_text = user_prompt if user_prompt else sentence
        explanation_request = tm.translate("ai.prompts.explanation_request", sentence=target_text)
        
        explanation_guidelines = tm.translate("ai.prompts.explanation_guidelines")
        language_instruction = tm.translate("ai.prompts.language_instruction")
        format_instruction = tm.translate("ai.prompts.format_instruction")
        writing_instruction = tm.translate("ai.prompts.writing_instruction")
        structure_instruction = tm.translate("ai.prompts.structure_instruction")
        
        # If we have both sentence and user_prompt, include the sentence context
        sentence_context = ""
        if user_prompt and sentence and sentence != user_prompt:
            sentence_context = f"\n\nThe user is asking about this in relation to the sentence: \"{sentence}\""
        
        return f"""{context_intro}

---
{context}
---

{explanation_request}{sentence_context}

{explanation_guidelines}
{language_instruction}
{format_instruction} 
{writing_instruction}
{structure_instruction}
"""
    
    def _create_study_mode_prompt(self, sentence: str, context: str, tm, user_prompt: str = None) -> str:
        """Create study mode prompt with Cruise personality."""
        # Get study mode specific translations
        agent_name = tm.translate("ai.prompts.study_mode.agent_name")
        personality = tm.translate("ai.prompts.study_mode.personality")
        approach = tm.translate("ai.prompts.study_mode.approach")
        context_intro = tm.translate("ai.prompts.study_mode.context_intro")
        
        # Use user_prompt if provided, otherwise use sentence
        target_text = user_prompt if user_prompt else sentence
        explanation_request = tm.translate("ai.prompts.study_mode.explanation_request", sentence=target_text)
        
        # Get guidelines and principles
        guidelines = tm.translate("ai.prompts.study_mode.guidelines")
        pedagogical_principles = tm.translate("ai.prompts.study_mode.pedagogical_principles")
        response_structure = tm.translate("ai.prompts.study_mode.response_structure")
        language_instruction = tm.translate("ai.prompts.study_mode.language_instruction")
        format_instruction = tm.translate("ai.prompts.study_mode.format_instruction")
        tone_instruction = tm.translate("ai.prompts.study_mode.tone_instruction")
        
        # Format guidelines and principles as bullet points
        guidelines_text = "\n".join([f"• {guideline}" for guideline in guidelines]) if isinstance(guidelines, list) else guidelines
        principles_text = "\n".join([f"• {principle}" for principle in pedagogical_principles]) if isinstance(pedagogical_principles, list) else pedagogical_principles
        
        # If we have both sentence and user_prompt, include the sentence context
        sentence_context = ""
        if user_prompt and sentence and sentence != user_prompt:
            sentence_context = f"\n\nThe user is asking about this in relation to the sentence: \"{sentence}\""
        
        return f"""{personality}

{approach}

{context_intro}

---
{context}
---

{explanation_request}{sentence_context}

**Your Educational Guidelines:**
{guidelines_text}

**Pedagogical Principles to Follow:**
{principles_text}

**Response Structure:**
{response_structure}

{language_instruction}
{format_instruction}
{tone_instruction}

Remember: You are {agent_name}, and your goal is to guide the student to understanding, not just provide answers.
"""

    def _stream_explanation(self, model: str, sentence: str, context: str, on_chunk: Callable[[str], None], on_done: Callable[[], None], study_mode: bool = False, user_prompt: str = None):
        """Stream the explanation from the Ollama API."""
        prompt = self._create_prompt(sentence, context, study_mode, user_prompt)
        
        print(f"DEBUG: Starting AI request for model: {model}")
        print(f"DEBUG: Sentence: {sentence}")
        print(f"DEBUG: User prompt: {user_prompt}")
        print(f"DEBUG: Study mode: {study_mode}")
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True
            }
            
            headers = {"Content-Type": "application/json"}
            
            print(f"DEBUG: Making request to {self.api_url}")
            with requests.post(self.api_url, data=json.dumps(payload), headers=headers, stream=True) as response:
                print(f"DEBUG: Response status: {response.status_code}")
                response.raise_for_status()
                chunk_count = 0
                for line in response.iter_lines():
                    if self.stop_event.is_set():
                        print("DEBUG: Stop event set, breaking")
                        break
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            chunk_count += 1
                            print(f"DEBUG: Received chunk {chunk_count}: {chunk[:50]}...")
                            try:
                                on_chunk(chunk)
                            except RuntimeError:
                                print("DEBUG: RuntimeError in on_chunk, widget deleted")
                                # Widget was deleted, stop processing
                                break
                        if data.get("done"):
                            print("DEBUG: Received done signal")
                            break
                print(f"DEBUG: Finished streaming, total chunks: {chunk_count}")
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request exception: {e}")
            try:
                on_chunk(f"\n\nError: {e}")
            except RuntimeError:
                # Widget was deleted, ignore error
                pass
        except Exception as e:
            print(f"DEBUG: Unexpected exception: {e}")
            try:
                on_chunk(f"\n\nUnexpected error: {e}")
            except RuntimeError:
                # Widget was deleted, ignore error
                pass
        finally:
            print("DEBUG: Calling on_done")
            try:
                on_done()
            except RuntimeError:
                print("DEBUG: RuntimeError in on_done, widget deleted")
                # Widget was deleted, ignore error
                pass

    def stop(self):
        """Stop the current streaming request."""
        self.stop_event.set()