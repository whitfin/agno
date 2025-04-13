CUSTOM_CSS = """
<style>
/* Main Styles */
.main-title {
    text-align: center;
    background: linear-gradient(45deg, #FF4B2B, #FF416C);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3em;
    font-weight: bold;
    padding: 1em 0;
}
.subtitle {
    text-align: center;
    color: #666;
    margin-bottom: 2em;
}
.stButton button {
    width: 100%;
    border-radius: 20px;
    margin: 0.2em 0;
    transition: all 0.3s ease;
}
.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}
.chat-container {
    border-radius: 15px;
    padding: 1em;
    margin: 1em 0;
    background-color: #f5f5f5;
}
/* Minor style adjustments for consistency */
.stChatMessage {
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
[data-testid="stChatMessageContent"] p {
    margin: 0;
    line-height: 1.6;
}
    [data-testid="stChatMessageContent"] pre code {
    white-space: pre-wrap !important;
    word-wrap: break-word !important;
}
[data-testid="stChatMessageContent"] [data-testid="stExpander"] {
    border: 1px solid #D1D5DB; /* Light border for expanders */
    border-radius: 5px;
}
[data-testid="stChatMessageContent"] [data-testid="stExpander"] summary {
    font-weight: 500;
}
.status-message {
    padding: 1em;
    border-radius: 10px;
    margin: 1em 0;
}
.success-message {
    background-color: #d4edda;
    color: #155724;
}
.error-message {
    background-color: #f8d7da;
    color: #721c24;
}
/* Fix chat input to bottom */
.stChatInputContainer {
    position: fixed;
    bottom: 0;
    width: calc(100% - 2rem); /* Adjust width considering potential padding */
    background-color: #ffffff; /* Match light theme background */
    padding: 1rem;
    border-top: 1px solid #e0e0e0; /* Add a subtle top border */
    z-index: 1000; /* Ensure it stays on top */
    margin-left: -1rem; /* Offset default padding if necessary */
}
/* Adjust main content padding to prevent overlap */
.main .block-container {
    padding-bottom: 7rem;
}

/* Dark mode adjustments */
@media (prefers-color-scheme: dark) {
    .stApp {
        background-color: #1F2937; /* Dark gray background */
        color: #D1D5DB;
    }
    .main-title {
        background: linear-gradient(45deg, #e98a79, #e78fa5);
        -webkit-background-clip: text;
    }
    .subtitle {
        color: #9CA3AF; /* Lighter gray */
    }
    .stChatMessage {
        background-color: #374151; /* Slightly lighter dark gray */
        box-shadow: none;
    }
        [data-testid="stChatMessageContent"] p {
        color: #D1D5DB;
    }
        [data-testid="stChatMessageContent"] [data-testid="stExpander"] {
        border: 1px solid #4B5563;
    }
        [data-testid="stChatMessageContent"] [data-testid="stExpander"] summary {
        color: #BFDBFE;
    }
    .chat-container {
        background-color: #2b2b2b;
    }
    .success-message {
            background-color: #1c3d24; /* Darker success */
            color: #a4edb5;
    }
    .error-message {
        background-color: #4a1c24; /* Darker error */
        color: #f8a7ae;
    }
    /* Dark mode chat input */
    .stChatInputContainer {
        background-color: #1F2937; /* Match dark theme background */
        border-top: 1px solid #4B5563;
    }
}
</style>
"""
