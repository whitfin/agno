# RunPod Model Integration Plan for Agno

## Overview
This plan outlines the integration of RunPod as a model provider in the Agno framework, allowing users to leverage RunPod's serverless GPU infrastructure for AI agent workloads.

## Understanding RunPod Architecture

### RunPod Core Components
1. **Endpoints**: Serverless inference endpoints that can host various AI models
2. **Jobs**: Individual inference requests with async/sync execution modes
3. **Streaming**: Real-time output streaming for long-running inference
4. **Templates**: Pre-configured environments for different models
5. **Serverless Workers**: Custom deployment units that can run any AI model

### RunPod API Structure
- **Synchronous API**: Immediate response for quick inference (`run_sync`)
- **Asynchronous API**: Job-based execution with polling (`run` + `status`/`output`)
- **Streaming API**: Real-time streaming for progressive outputs (`stream`)
- **Health Monitoring**: Endpoint health and queue management

## Integration Strategy

### 1. Model Provider Implementation

#### Core Architecture
```python
@dataclass
class RunPod(Model):
    """
    RunPod model provider for Agno agents.
    
    Supports both:
    - Pre-deployed endpoints (endpoint_id)
    - Custom serverless workers (for advanced use cases)
    """
    
    # Provider identification
    id: str = "endpoint-id-or-model-name"
    name: str = "RunPod"
    provider: str = "RunPod"
    
    # RunPod-specific configuration
    endpoint_id: str  # Required: RunPod endpoint identifier
    api_key: Optional[str] = None  # RunPod API key
    
    # Execution modes
    execution_mode: str = "sync"  # "sync", "async", "stream"
    timeout: int = 300  # Max wait time for async jobs
    
    # Model configuration
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    
    # Advanced options
    webhook_url: Optional[str] = None  # For async job notifications
    request_params: Optional[Dict[str, Any]] = None
```

#### Implementation Approach
We'll implement RunPod as a **custom model provider** (not OpenAI-like) because:
1. RunPod has its own unique job-based API structure
2. Supports async execution patterns not found in chat completion APIs
3. Provides streaming capabilities with different semantics
4. Has endpoint-specific configuration requirements

### 2. Feature Support Matrix

| Feature | Support Level | Implementation Notes |
|---------|---------------|---------------------|
| **Core Inference** |
| Synchronous calls | ✅ Full | Via `run_sync` API |
| Asynchronous calls | ✅ Full | Via `run` + polling |
| Streaming | ✅ Full | Via `stream` API |
| **Message Handling** |
| Text messages | ✅ Full | Standard text input/output |
| System prompts | ✅ Full | Embedded in input |
| Multi-turn conversations | ✅ Full | Context management |
| **Advanced Features** |
| Tool/Function calling | ⚠️ Partial | Depends on deployed model |
| Structured outputs | ⚠️ Partial | Depends on deployed model |
| Image inputs | ⚠️ Partial | Depends on endpoint capabilities |
| Audio inputs | ⚠️ Partial | Depends on endpoint capabilities |
| **Operational** |
| Error handling | ✅ Full | Comprehensive error mapping |
| Rate limiting | ✅ Full | Built into RunPod API |
| Cost tracking | ✅ Full | Via usage metrics |

### 3. API Integration Details

#### Message Format Transformation
```python
def _format_messages_for_runpod(self, messages: List[Message]) -> Dict[str, Any]:
    """
    Convert Agno messages to RunPod input format.
    
    RunPod endpoints expect custom input formats depending on the deployed model.
    We'll support common patterns:
    - Chat completion format (for LLM endpoints)
    - Custom input schemas (configurable)
    """
    
    # Standard chat format
    if self.input_format == "chat":
        return {
            "messages": [self._format_message(msg) for msg in messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p
        }
    
    # Custom format (user-defined schema)
    elif self.input_format == "custom":
        return self.custom_formatter(messages)
    
    # Raw format (direct message content)
    else:
        return {"input": messages[-1].content}
```

#### Response Parsing
```python
def parse_provider_response(self, response: Dict[str, Any], **kwargs) -> ModelResponse:
    """
    Parse RunPod job output into Agno ModelResponse.
    
    RunPod responses vary by endpoint but typically contain:
    - output: The main model output
    - status: Job completion status
    - metrics: Execution metrics
    """
    
    model_response = ModelResponse()
    
    # Handle different response formats
    if isinstance(response.get("output"), str):
        model_response.content = response["output"]
    elif isinstance(response.get("output"), dict):
        # Structured output
        model_response.content = response["output"].get("content", "")
        model_response.tool_calls = response["output"].get("tool_calls", [])
    
    # Extract usage metrics
    if "metrics" in response:
        model_response.response_usage = self._parse_usage(response["metrics"])
    
    return model_response
```

### 4. Execution Modes

#### 4.1 Synchronous Mode (Default)
- Uses RunPod's `run_sync` API
- Blocks until completion or timeout
- Best for quick inference (<5 minutes)
- Simple error handling

#### 4.2 Asynchronous Mode
- Uses RunPod's `run` API with job polling
- Non-blocking job submission
- Suitable for long-running inference
- Requires job status monitoring

#### 4.3 Streaming Mode
- Uses RunPod's streaming API
- Real-time output generation
- Perfect for chat applications
- Supports progressive response building

### 5. Error Handling Strategy

#### RunPod Error Mapping
```python
class RunPodErrorHandler:
    """Maps RunPod errors to Agno exceptions."""
    
    ERROR_MAPPING = {
        "UNAUTHORIZED": ModelProviderError,
        "ENDPOINT_NOT_FOUND": ModelProviderError,
        "INSUFFICIENT_CREDITS": ModelRateLimitError,
        "WORKER_TIMEOUT": ModelProviderError,
        "QUEUE_FULL": ModelRateLimitError,
    }
    
    def handle_error(self, error_response: Dict[str, Any]) -> None:
        error_type = error_response.get("error", {}).get("type")
        error_message = error_response.get("error", {}).get("message", "Unknown error")
        
        exception_class = self.ERROR_MAPPING.get(error_type, ModelProviderError)
        raise exception_class(
            message=error_message,
            model_name=self.name,
            model_id=self.id
        )
```

### 6. Configuration Examples

#### Basic Chat Model
```python
from agno.models.runpod import RunPod

# Basic configuration for a chat model endpoint
chat_model = RunPod(
    endpoint_id="your-chat-endpoint-id",
    api_key="your-runpod-api-key",
    execution_mode="sync",
    max_tokens=1000,
    temperature=0.7
)

agent = Agent(model=chat_model)
```

#### Advanced Streaming Configuration
```python
# Streaming configuration for real-time chat
streaming_model = RunPod(
    endpoint_id="your-streaming-endpoint-id",
    execution_mode="stream",
    input_format="chat",
    timeout=600  # 10 minutes max
)

agent = Agent(model=streaming_model)
```

#### Custom Model Configuration
```python
# Custom input/output format for specialized models
custom_model = RunPod(
    endpoint_id="your-custom-endpoint-id",
    input_format="custom",
    custom_formatter=lambda msgs: {"prompt": msgs[-1].content, "mode": "creative"},
    output_parser=lambda resp: resp.get("generated_text", "")
)
```

### 7. File Structure

```
libs/agno/agno/models/runpod/
├── __init__.py          # Exports (RunPod class)
├── runpod.py           # Main implementation
├── errors.py           # Error handling utilities
├── formatters.py       # Input/output formatters
└── examples/           # Usage examples
    ├── basic_chat.py
    ├── streaming_chat.py
    └── custom_model.py
```

### 8. Implementation Steps

#### Phase 1: Core Implementation
1. ✅ Create base RunPod model class
2. ✅ Implement synchronous inference (`invoke`)
3. ✅ Implement async inference (`ainvoke`)
4. ✅ Add basic error handling
5. ✅ Create response parsing logic

#### Phase 2: Streaming Support
1. ✅ Implement streaming (`invoke_stream`)
2. ✅ Implement async streaming (`ainvoke_stream`)
3. ✅ Add streaming response parsing
4. ✅ Handle streaming errors

#### Phase 3: Advanced Features
1. ✅ Add custom input formatters
2. ✅ Support tool calling (if endpoint supports it)
3. ✅ Add usage tracking and metrics
4. ✅ Implement retry logic

#### Phase 4: Documentation and Testing
1. ✅ Create comprehensive examples
2. ✅ Add integration tests
3. ✅ Write usage documentation
4. ✅ Performance optimization

### 9. Testing Strategy

#### Unit Tests
- Message formatting and parsing
- Error handling scenarios
- Configuration validation
- Response transformation

#### Integration Tests
- Real RunPod endpoint calls
- Streaming functionality
- Async job management
- Error scenarios

#### Performance Tests
- Latency measurements
- Throughput testing
- Memory usage profiling
- Concurrent request handling

### 10. Documentation Requirements

#### User Documentation
1. **Quick Start Guide**: Basic setup and usage
2. **Configuration Reference**: All parameters explained
3. **Examples Collection**: Common use cases
4. **Troubleshooting Guide**: Common issues and solutions

#### Developer Documentation
1. **Architecture Overview**: Implementation details
2. **API Reference**: Complete method documentation
3. **Extension Guide**: Custom formatters and parsers
4. **Contributing Guide**: Development setup and guidelines

### 11. Future Enhancements

#### Planned Features
1. **Auto-scaling**: Dynamic endpoint scaling based on load
2. **Model Discovery**: Automatic detection of endpoint capabilities
3. **Cost Optimization**: Intelligent routing to cost-effective instances
4. **Multi-endpoint**: Load balancing across multiple endpoints

#### Potential Integrations
1. **RunPod Templates**: Direct integration with template management
2. **Custom Deployments**: Automated model deployment
3. **Monitoring**: Advanced metrics and logging
4. **Caching**: Response caching for cost optimization

### 12. Success Metrics

#### Technical Metrics
- **Latency**: <2s for sync calls, <100ms for streaming chunks
- **Reliability**: >99.5% success rate for valid requests
- **Throughput**: Support for 100+ concurrent requests
- **Error Rate**: <0.5% for infrastructure-related errors

#### User Experience Metrics
- **Setup Time**: <5 minutes from installation to first inference
- **Documentation Coverage**: 100% of public APIs documented
- **Example Coverage**: Examples for all major use cases
- **Community Adoption**: Active usage and feedback

This comprehensive plan ensures a robust, feature-complete RunPod integration that leverages the full capabilities of RunPod's serverless infrastructure while maintaining compatibility with Agno's agent framework.
