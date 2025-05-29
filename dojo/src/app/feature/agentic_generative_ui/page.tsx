"use client";
import React, { useState } from "react";
import "@copilotkit/react-ui/styles.css";
import "./style.css";
import { CopilotKit, useCoAgentStateRender, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

const AgenticGenerativeUI: React.FC = () => {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      showDevConsole={false}
      // agent lock to the relevant agent
      agent="agentiveGenerativeUIAgent"
    >
      <Chat />
    </CopilotKit>
  );
};

interface AgentState {
  steps: {
    description: string;
    status: "pending" | "active" | "completed";
  }[];
}

const Chat = () => {
  const [currentSteps, setCurrentSteps] = useState<AgentState>({ steps: [] });

  // Handle update_steps tool call
  useCopilotAction({
    name: "update_steps",
    parameters: [
      {
        name: "steps",
        type: "object[]",
        description: "Array of steps with their current status",
      },
    ],
    handler: async ({ steps }: { steps: Array<{ description: string; status: "pending" | "completed" }> }) => {
      console.log("update_steps called with:", steps);
      // Convert to our internal format with "active" status support
      const convertedSteps = steps.map(step => ({
        ...step,
        status: step.status as "pending" | "active" | "completed"
      }));
      setCurrentSteps({ steps: convertedSteps });
      return "Steps updated successfully";
    },
  });

  // Handle start_step tool call
  useCopilotAction({
    name: "start_step",
    parameters: [
      {
        name: "step_name",
        type: "string",
        description: "Name or description of the step being started",
      },
    ],
    handler: async ({ step_name }: { step_name: string }) => {
      console.log("start_step called with:", step_name);
      setCurrentSteps(prev => ({
        steps: prev.steps.map(step =>
          step.description === step_name
            ? { ...step, status: "active" as const }
            : step
        )
      }));
      return `Step "${step_name}" started`;
    },
  });

  // Handle complete_step tool call
  useCopilotAction({
    name: "complete_step",
    parameters: [
      {
        name: "step_name",
        type: "string",
        description: "Name or description of the step being completed",
      },
    ],
    handler: async ({ step_name }: { step_name: string }) => {
      console.log("complete_step called with:", step_name);
      setCurrentSteps(prev => ({
        steps: prev.steps.map(step =>
          step.description === step_name
            ? { ...step, status: "completed" as const }
            : step
        )
      }));
      return `Step "${step_name}" completed`;
    },
  });

  // Use the local state for rendering if available, otherwise fall back to agent state
  useCoAgentStateRender<AgentState>({
    name: "agentiveGenerativeUIAgent",
    render: ({ state }) => {
      const stateToRender = currentSteps.steps.length > 0 ? currentSteps : state;
      
      if (!stateToRender?.steps || stateToRender.steps.length === 0) {
        return null;
      }

      return (
        <div className="flex">
          <div className="bg-gray-100 rounded-lg w-[500px] p-4 text-black space-y-2">
            {stateToRender.steps.map((step, index) => {
              if (step.status === "completed") {
                return (
                  <div key={index} className="text-sm flex items-center">
                    <span className="text-green-600 mr-2">✓</span>
                    <span className="line-through text-gray-600">{step.description}</span>
                  </div>
                );
              } else if (step.status === "active") {
                return (
                  <div
                    key={index}
                    className="text-lg font-bold text-blue-700 flex items-center"
                  >
                    <Spinner />
                    <span>{step.description}</span>
                  </div>
                );
              } else {
                // pending status
                return (
                  <div key={index} className="text-sm flex items-center text-gray-500">
                    <span className="mr-2">○</span>
                    <span>{step.description}</span>
                  </div>
                );
              }
            })}
          </div>
        </div>
      );
    },
  });

  return (
    <div className="flex justify-center items-center h-full w-full">
      <div className="w-8/10 h-8/10 rounded-lg">
        <CopilotChat
          className="h-full rounded-2xl"
          labels={{
            initial:
              "Hi, I'm an agent! I can help you with anything you need and will show you progress as I work. What can I do for you?",
          }}
        />
      </div>
    </div>
  );
};

function Spinner() {
  return (
    <svg
      className="mr-2 size-4 animate-spin text-blue-500"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      ></circle>
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      ></path>
    </svg>
  );
}

export default AgenticGenerativeUI;
