"use client";
import React, { useState } from "react";
import "@copilotkit/react-ui/styles.css";
import "./style.css";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";

const ChatWithActions: React.FC = () => {
  const [backgroundColor, setBackgroundColor] = useState("#ffffff");

  // Define the frontend action that the agent can call
  useCopilotAction({
    name: "setBackgroundColor",
    description: "Set the background color of the chat interface",
    parameters: [
      {
        name: "color",
        type: "string",
        description: "The CSS color value (hex, rgb, gradient, etc.)",
        required: true,
      },
    ],
    handler: ({ color }) => {
      setBackgroundColor(color);
      return `Background color changed to ${color}`;
    },
  });

  return (
    <div 
      className="flex justify-center items-center h-full w-full transition-all duration-500"
      style={{ background: backgroundColor }}
    >
      <div className="w-8/10 h-8/10 rounded-lg">
        <CopilotChat
          className="h-full rounded-2xl"
          labels={{
            initial: "Hi! I can help you change the background color. Try asking me to set it to a gradient or any color you like!",
          }}
        />
      </div>
    </div>
  );
};

const AgenticChat: React.FC = () => {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      showDevConsole={false}
      agent="agenticChatAgent"
    >
      <ChatWithActions />
    </CopilotKit>
  );
};

export default AgenticChat;
