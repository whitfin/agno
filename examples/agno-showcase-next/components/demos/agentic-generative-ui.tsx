"use client";

import React, { useState, useEffect } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface Step {
  id: string;
  title: string;
  status: "pending" | "in-progress" | "completed";
  description?: string;
}

export function AgenticGenerativeUIDemo() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [currentTask, setCurrentTask] = useState<string>("");

  // Make the current steps readable to the agent
  useCopilotReadable({
    description: "Current task steps",
    value: steps,
  });

  // Define actions that the agent can use to update the UI
  useCopilotAction({
    name: "update_steps",
    description: "Update the list of steps for the current task",
    parameters: [
      {
        name: "steps",
        type: "object[]",
        description: "Array of step objects",
        attributes: [
          {
            name: "id",
            type: "string",
            description: "Unique identifier for the step",
          },
          {
            name: "title",
            type: "string",
            description: "Title of the step",
          },
          {
            name: "description",
            type: "string",
            description: "Optional description of the step",
            required: false,
          },
        ],
      },
    ],
    handler: async ({ steps: newSteps }) => {
      setSteps(
        newSteps.map((step: any) => ({
          ...step,
          status: "pending" as const,
        }))
      );
    },
  });

  useCopilotAction({
    name: "start_step",
    description: "Mark a step as in progress",
    parameters: [
      {
        name: "stepId",
        type: "string",
        description: "ID of the step to start",
      },
    ],
    handler: async ({ stepId }) => {
      setSteps((prev) =>
        prev.map((step) =>
          step.id === stepId ? { ...step, status: "in-progress" } : step
        )
      );
    },
  });

  useCopilotAction({
    name: "complete_step",
    description: "Mark a step as completed",
    parameters: [
      {
        name: "stepId",
        type: "string",
        description: "ID of the step to complete",
      },
    ],
    handler: async ({ stepId }) => {
      setSteps((prev) =>
        prev.map((step) =>
          step.id === stepId ? { ...step, status: "completed" } : step
        )
      );
    },
  });

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Task Progress</h2>
        
        {steps.length === 0 ? (
          <p className="text-gray-500">
            Ask the agent to help you with a task, and it will break it down into steps!
          </p>
        ) : (
          <div className="space-y-3">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`p-4 rounded-lg border-2 transition-all ${
                  step.status === "completed"
                    ? "border-green-500 bg-green-50"
                    : step.status === "in-progress"
                    ? "border-blue-500 bg-blue-50 animate-pulse"
                    : "border-gray-300 bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">{step.title}</h3>
                    {step.description && (
                      <p className="text-sm text-gray-600 mt-1">
                        {step.description}
                      </p>
                    )}
                  </div>
                  <div className="ml-4">
                    {step.status === "completed" && (
                      <span className="text-green-600">✓</span>
                    )}
                    {step.status === "in-progress" && (
                      <span className="text-blue-600">⏳</span>
                    )}
                    {step.status === "pending" && (
                      <span className="text-gray-400">○</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-blue-50 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Try asking:</strong> "Help me plan a birthday party" or "Guide me through making a website"
        </p>
      </div>
    </div>
  );
} 