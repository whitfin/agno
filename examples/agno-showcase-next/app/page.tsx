"use client";

import React, { useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

// Import your demo components
import { AgenticGenerativeUIDemo } from "@/components/demos/agentic-generative-ui";
import { SharedStateDemo } from "@/components/demos/shared-state";
import { ToolBasedGenerativeUIDemo } from "@/components/demos/tool-based-generative-ui";
import { AgenticChatDemo } from "@/components/demos/agentic-chat";
import { HumanInTheLoopDemo } from "@/components/demos/human-in-the-loop";
import { PredictiveStateUpdatesDemo } from "@/components/demos/predictive-state-updates";

// Demo configuration
const DEMOS = [
  {
    id: "agentic-generative-ui",
    title: "Agentic Generative UI",
    component: AgenticGenerativeUIDemo,
    agentId: "agentiveGenerativeUIAgent",
  },
  {
    id: "shared-state",
    title: "Shared State",
    component: SharedStateDemo,
    agentId: "sharedStateAgent",
  },
  {
    id: "tool-based-generative-ui",
    title: "Tool-based Generative UI",
    component: ToolBasedGenerativeUIDemo,
    agentId: "haikuGeneratorAgent",
  },
  {
    id: "agentic-chat",
    title: "Agentic Chat",
    component: AgenticChatDemo,
    agentId: "calculatorAgent",
  },
  {
    id: "human-in-the-loop",
    title: "Human-in-the-Loop",
    component: HumanInTheLoopDemo,
    agentId: "weatherAgent",
  },
  {
    id: "predictive-state-updates",
    title: "Predictive State Updates",
    component: PredictiveStateUpdatesDemo,
    agentId: "predictiveStateAgent",
  },
];

export default function Home() {
  const [selectedDemo, setSelectedDemo] = useState(DEMOS[0]);

  const DemoComponent = selectedDemo.component;

  return (
    <CopilotKit 
      runtimeUrl="/api/copilotkit"
      agent={selectedDemo.agentId}
    >
      <CopilotSidebar
        defaultOpen={true}
        clickOutsideToClose={false}
        className="h-screen"
      >
        <div className="flex h-screen">
          {/* Demo selector sidebar */}
          <div className="w-64 bg-gray-100 p-4 overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">AG-UI Demos</h2>
            <nav className="space-y-2">
              {DEMOS.map((demo) => (
                <button
                  key={demo.id}
                  onClick={() => setSelectedDemo(demo)}
                  className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                    selectedDemo.id === demo.id
                      ? "bg-blue-500 text-white"
                      : "hover:bg-gray-200"
                  }`}
                >
                  {demo.title}
                </button>
              ))}
            </nav>
          </div>

          {/* Demo content area */}
          <div className="flex-1 p-8 overflow-y-auto">
            <h1 className="text-2xl font-bold mb-4">{selectedDemo.title}</h1>
            <DemoComponent />
          </div>
        </div>
      </CopilotSidebar>
    </CopilotKit>
  );
}
