from typing import List, Optional, Tuple, Dict, Any
import re

from core.models.prompt import Prompt
from core.services.prompt_service import PromptService


class InteractivePromptService(PromptService):
    """
    Service for handling interactive prompts with confirmation markers.
    Extends the base PromptService to add support for processing prompts
    with <<AWAIT_CONFIRM>> markers and managing the interactive flow.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_step = 0
        self._confirmation_points = []
        self._processed_content = ""

    def process_interactive_prompt(self, prompt_content: str) -> Tuple[str, bool, Optional[str]]:
        """
        Process a prompt with confirmation markers.
        
        Args:
            prompt_content: The content of the prompt to process
            
        Returns:
            Tuple containing:
            - The processed content up to the next confirmation point
            - Boolean indicating if confirmation is needed
            - The confirmation message if confirmation is needed, None otherwise
        """
        if not prompt_content:
            return "", False, None
            
        # Reset state for new prompt
        self._current_step = 0
        self._confirmation_points = []
        self._processed_content = ""
        
        # Find all confirmation points in the prompt
        pattern = r'<<AWAIT_CONFIRM:\s*(.*?)\s*>>'
        matches = re.finditer(pattern, prompt_content)
        
        # Store the positions and messages of confirmation points
        for match in matches:
            self._confirmation_points.append({
                'position': match.start(),
                'message': match.group(1),
                'full_match': match.group(0)
            })
            
        # If no confirmation points, return the full content
        if not self._confirmation_points:
            return prompt_content, False, None
            
        # Get content up to the first confirmation point
        first_point = self._confirmation_points[0]
        content_until_first_point = prompt_content[:first_point['position']]
        
        # Store the processed content
        self._processed_content = content_until_first_point
        
        return content_until_first_point, True, first_point['message']
        
    def continue_after_confirmation(self, prompt_content: str) -> Tuple[str, bool, Optional[str]]:
        """
        Continue processing the prompt after a confirmation point.
        
        Args:
            prompt_content: The full content of the prompt
            
        Returns:
            Tuple containing:
            - The next chunk of content up to the next confirmation point
            - Boolean indicating if more confirmation is needed
            - The next confirmation message if needed, None otherwise
        """
        # Increment the current step
        self._current_step += 1
        
        # If we've processed all confirmation points, return the rest of the content
        if self._current_step >= len(self._confirmation_points):
            # Get content after the last confirmation point
            last_point = self._confirmation_points[-1]
            last_point_end = last_point['position'] + len(last_point['full_match'])
            remaining_content = prompt_content[last_point_end:]
            
            # Append to processed content
            self._processed_content += remaining_content
            
            return remaining_content, False, None
            
        # Get content between current and next confirmation point
        current_point = self._confirmation_points[self._current_step - 1]
        next_point = self._confirmation_points[self._current_step]
        
        current_point_end = current_point['position'] + len(current_point['full_match'])
        content_between_points = prompt_content[current_point_end:next_point['position']]
        
        # Append to processed content
        self._processed_content += content_between_points
        
        return content_between_points, True, next_point['message']
        
    def get_full_processed_content(self) -> str:
        """
        Get the full processed content so far.
        
        Returns:
            The processed content with confirmation markers removed
        """
        return self._processed_content
        
    def get_interactive_prompt(self, user_id: Optional[int], action_type: Optional[str]) -> Tuple[Optional[Prompt], str, bool, Optional[str]]:
        """
        Get the most relevant prompt and process it for interactive use.
        
        Args:
            user_id: The ID of the user
            action_type: The type of action
            
        Returns:
            Tuple containing:
            - The Prompt object
            - The processed content up to the next confirmation point
            - Boolean indicating if confirmation is needed
            - The confirmation message if needed, None otherwise
        """
        prompt = self.get_most_relevant_prompt(user_id, action_type)
        if not prompt:
            return None, "", False, None
            
        content = getattr(prompt, "content", "")
        processed_content, needs_confirmation, confirmation_message = self.process_interactive_prompt(content)
        
        return prompt, processed_content, needs_confirmation, confirmation_message