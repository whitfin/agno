from dataclasses import dataclass, field
import json
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple


from agno.memory.summary import SessionSummary
from agno.models.base import Model
from agno.models.message import Message
from agno.utils.log import log_debug, log_info, log_warning
from agno.utils.string import parse_response_model_str

@dataclass
class SessionSummary:
    """Model for Session Summary."""

    summary: str = field(
        ...,
        description="Summary of the session. Be concise and focus on only important information. Do not make anything up.",
    )
    topics: Optional[List[str]] = field(default=None, description="Topics discussed in the session.")

    def to_dict(self) -> Dict[str, Any]:
        response = {
            "summary": self.summary,
            "topics": self.topics,
        }
        return {k: v for k, v in response.items() if v is not None}

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SessionSummarizer:
    model: Model

    def update_model(self) -> None:
        if self.model.supports_native_structured_outputs:
            self.model.response_format = SessionSummary
            self.model.structured_outputs = True
        
        elif self.model.supports_json_schema_outputs:
            self.model.response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": SessionSummary.__name__,
                    "schema": SessionSummary.model_json_schema(),
                },
            }
        else:
            self.model.response_format = {"type": "json_object"}


    def get_system_message(self, messages_for_summarization: List[Dict[str, str]]) -> Message:
        # -*- Return a system message for summarization
        system_prompt = dedent("""\
        Analyze the following conversation between a user and an assistant, and extract the following details:
          - Summary (str): Provide a concise summary of the session, focusing on important information that would be helpful for future interactions.
          - Topics (Optional[List[str]]): List the topics discussed in the session.
        Please ignore any frivolous information.

        Conversation:
        """)
        conversation = []
        for message_pair in messages_for_summarization:
            conversation.append(f"User: {message_pair['user']}")
            if "assistant" in message_pair:
                conversation.append(f"Assistant: {message_pair['assistant']}")
            elif "model" in message_pair:
                conversation.append(f"Assistant: {message_pair['model']}")

        system_prompt += "\n".join(conversation)

        if not self.model.supports_native_structured_outputs:
            system_prompt += "\n\nProvide your output as a JSON containing the following fields:"
            json_schema = SessionSummary.model_json_schema()
            response_model_properties = {}
            json_schema_properties = json_schema.get("properties")
            if json_schema_properties is not None:
                for field_name, field_properties in json_schema_properties.items():
                    formatted_field_properties = {
                        prop_name: prop_value
                        for prop_name, prop_value in field_properties.items()
                        if prop_name != "title"
                    }
                    response_model_properties[field_name] = formatted_field_properties

            if len(response_model_properties) > 0:
                system_prompt += "\n<json_fields>"
                system_prompt += f"\n{json.dumps([key for key in response_model_properties.keys() if key != '$defs'])}"
                system_prompt += "\n</json_fields>"
                system_prompt += "\nHere are the properties for each field:"
                system_prompt += "\n<json_field_properties>"
                system_prompt += f"\n{json.dumps(response_model_properties, indent=2)}"
                system_prompt += "\n</json_field_properties>"

            system_prompt += "\nStart your response with `{` and end it with `}`."
            system_prompt += "\nYour output will be passed to json.loads() to convert it to a Python object."
            system_prompt += "\nMake sure it only contains valid JSON."
        return Message(role="system", content=system_prompt)

    def run(
        self,
        message_pairs: List[Tuple[Message, Message]],
    ) -> Optional[SessionSummary]:
        log_debug("SessionSummarizer Start", center=True)

        if message_pairs is None or len(message_pairs) == 0:
            log_info("No message pairs provided for summarization.")
            return None

        # Update the Model (set defaults, add logit etc.)
        self.update_model()

        # Convert the message pairs to a list of dictionaries
        messages_for_summarization: List[Dict[str, str]] = []
        for message_pair in message_pairs:
            user_message, assistant_message = message_pair
            messages_for_summarization.append(
                {
                    user_message.role: user_message.get_content_string(),
                    assistant_message.role: assistant_message.get_content_string(),
                }
            )

        # Prepare the List of messages to send to the Model
        messages_for_model: List[Message] = [
            self.get_system_message(messages_for_summarization),
            # For models that require a non-system message
            Message(role="user", content="Provide the summary of the conversation."),
        ]

        # Generate a response from the Model (includes running function calls)
        response = self.model.response(messages=messages_for_model)
        log_debug("SessionSummarizer End", center=True)

        # If the model natively supports structured outputs, the parsed value is already in the structured format
        if self.model.supports_native_structured_outputs and response.parsed is not None and isinstance(response.parsed, SessionSummary):
            return response.parsed

        # Otherwise convert the response to the structured format
        if isinstance(response.content, str):
            try:
                session_summary = parse_response_model_str(response.content, self.response_model)

                # Update RunResponse
                if session_summary is not None:
                    return session_summary
                else:
                    log_warning("Failed to convert session_summary response to SessionSummary")
            except Exception as e:
                log_warning(f"Failed to convert session_summary response to SessionSummary: {e}")

        return None

    async def arun(
        self,
        message_pairs: List[Tuple[Message, Message]],
    ) -> Optional[SessionSummary]:
        log_debug("SessionSummarizer Start", center=True)

        if message_pairs is None or len(message_pairs) == 0:
            log_info("No message pairs provided for summarization.")
            return None

        # Update the Model (set defaults, add logit etc.)
        self.update_model()

        # Convert the message pairs to a list of dictionaries
        messages_for_summarization: List[Dict[str, str]] = []
        for message_pair in message_pairs:
            user_message, assistant_message = message_pair
            messages_for_summarization.append(
                {
                    user_message.role: user_message.get_content_string(),
                    assistant_message.role: assistant_message.get_content_string(),
                }
            )

        # Prepare the List of messages to send to the Model
        messages_for_model: List[Message] = [
            self.get_system_message(messages_for_summarization),
            # For models that require a non-system message
            Message(role="user", content="Provide the summary of the conversation."),
        ]

        # Generate a response from the Model (includes running function calls)
        response = await self.model.aresponse(messages=messages_for_model)
        log_debug("SessionSummarizer End", center=True)

        # If the model natively supports structured outputs, the parsed value is already in the structured format
        if self.model.supports_native_structured_outputs and response.parsed is not None and isinstance(response.parsed, SessionSummary):
            return response.parsed

        # Otherwise convert the response to the structured format
        if isinstance(response.content, str):
            try:
                session_summary = parse_response_model_str(response.content, self.response_model)

                # Update RunResponse
                if session_summary is not None:
                    return session_summary
                else:
                    log_warning("Failed to convert session_summary response to SessionSummary")
            except Exception as e:
                log_warning(f"Failed to convert session_summary response to SessionSummary: {e}")
        return None
