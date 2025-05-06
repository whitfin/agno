from dataclasses import dataclass
from datetime import datetime
from os import getenv
from typing import Any, Dict, Optional

try:
    from langfuse import Langfuse
except ImportError:
    raise ImportError("`langfuse` not installed. Please install using `pip install langfuse`")


@dataclass
class LangfuseObservability:
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: Optional[str] = None
    release: Optional[str] = None
    debug: Optional[bool] = False
    threads: Optional[int] = None
    max_retries: Optional[int] = None
    timeout: Optional[int] = None
    sample_rate: Optional[float] = None

    request_params: Optional[Dict[str, Any]] = None
    client: Optional[Langfuse] = None

    _current_trace_id: Optional[str] = None
    _current_span_id: Optional[str] = None
    _current_generation_id: Optional[str] = None

    def get_client(self):
        if self.client is not None:
            return self.client

        self.public_key = self.public_key or getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = self.secret_key or getenv("LANGFUSE_SECRET_KEY")

        if not self.public_key or not self.secret_key:
            raise ValueError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")

        self.host = self.host or getenv("LANGFUSE_HOST")
        self.release = self.release or getenv("LANGFUSE_RELEASE")
        self.debug = self.debug or getenv("LANGFUSE_DEBUG")
        self.threads = self.threads or getenv("LANGFUSE_THREADS")
        self.max_retries = self.max_retries or getenv("LANGFUSE_MAX_RETRIES")
        self.timeout = self.timeout or getenv("LANGFUSE_TIMEOUT")
        self.sample_rate = self.sample_rate or getenv("LANGFUSE_SAMPLE_RATE")

        self.request_params = self.request_params or {}

        langfuse = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=self.host,
            release=self.release,
            debug=self.debug,
            threads=self.threads,
            max_retries=self.max_retries,
            timeout=self.timeout,
            sample_rate=self.sample_rate,
        )
        self.client = langfuse
        return self.client

    def trace(
        self,
        name: Optional[str] = None,
        input_dict: Optional[Dict[str, Any]] = None,
        output_dict: Optional[Dict[str, Any]] = None,
    ):
        self._current_span_id = None
        self._current_generation_id = None
        trace = self.get_client().trace(name=name, input=input_dict, output=output_dict, **self.request_params)
        self._current_trace_id = trace.id

    def start_span(self, name: str, input_dict: Optional[Dict[str, Any]] = None):
        start_time = datetime.now()
        span = self.get_client().span(
            trace_id=self._current_trace_id, name=name, start_time=start_time, input=input_dict, **self.request_params
        )
        self._current_span_id = span.id

    def end_span(self, output_dict: Optional[Dict[str, Any]] = None):
        end_time = datetime.now()
        self.get_client().span(id=self._current_span_id, output=output_dict, end_time=end_time)
        self._current_span_id = None

    def start_generation(self, name: str, model: str, input_dict: Optional[Dict[str, Any]] = None):
        start_time = datetime.now()
        generation = self.get_client().generation(
            trace_id=self._current_trace_id,
            name=name,
            model=model,
            input=input_dict,
            start_time=start_time,
            **self.request_params,
        )
        self._current_generation_id = generation.id

    def end_generation(
        self, output_dict: Optional[Dict[str, Any]] = None, usage_details_dict: Optional[Dict[str, Any]] = None
    ):
        end_time = datetime.now()
        self.get_client().generation(
            id=self._current_generation_id, output=output_dict, usage_details=usage_details_dict, end_time=end_time
        )
        self._current_generation_id = None

    def create_event(
        self, name: str, input_dict: Optional[Dict[str, Any]] = None, output_dict: Optional[Dict[str, Any]] = None
    ):
        start_time = datetime.now()
        self.get_client().event(
            trace_id=self._current_trace_id,
            parent_observation_id=self._current_span_id,
            name=name,
            start_time=start_time,
            input=input_dict,
            output=output_dict,
            **self.request_params,
        )
