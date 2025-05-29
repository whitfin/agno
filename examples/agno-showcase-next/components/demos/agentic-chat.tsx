"use client";

import React, { useState } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface Calculation {
  id: string;
  expression: string;
  steps: string[];
  result: number;
  timestamp: string;
}

export function AgenticChatDemo() {
  const [calculations, setCalculations] = useState<Calculation[]>([]);
  const [currentExpression, setCurrentExpression] = useState<string>("");

  // Make calculations readable to the agent
  useCopilotReadable({
    description: "Calculation history",
    value: calculations,
  });

  // Calculator action
  useCopilotAction({
    name: "calculate",
    description: "Perform a mathematical calculation with step-by-step explanation",
    parameters: [
      {
        name: "expression",
        type: "string",
        description: "Mathematical expression to calculate",
      },
      {
        name: "steps",
        type: "object[]",
        description: "Step-by-step calculation process",
        attributes: [
          {
            name: "step",
            type: "string",
            description: "Description of the calculation step",
          },
        ],
      },
      {
        name: "result",
        type: "number",
        description: "Final result of the calculation",
      },
    ],
    handler: async ({ expression, steps, result }) => {
      const newCalculation: Calculation = {
        id: Date.now().toString(),
        expression,
        steps: steps.map((s: any) => s.step),
        result,
        timestamp: new Date().toLocaleTimeString(),
      };
      setCalculations((prev) => [newCalculation, ...prev]);
      return `Calculated: ${expression} = ${result}`;
    },
  });

  // Clear history action
  useCopilotAction({
    name: "clear_calculations",
    description: "Clear all calculation history",
    parameters: [],
    handler: async () => {
      setCalculations([]);
      return "Calculation history cleared";
    },
  });

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Smart Calculator</h2>
        
        {/* Current expression input */}
        <div className="mb-6">
          <input
            type="text"
            value={currentExpression}
            onChange={(e) => setCurrentExpression(e.target.value)}
            placeholder="Type an expression or ask the agent..."
            className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Calculation history */}
        {calculations.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No calculations yet.</p>
            <p className="text-sm text-gray-400 mt-2">
              Ask the agent to calculate something!
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {calculations.map((calc) => (
              <div
                key={calc.id}
                className="border rounded-lg p-4 bg-gray-50"
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-mono text-lg font-semibold">
                      {calc.expression} = {calc.result}
                    </h3>
                    <p className="text-sm text-gray-500">{calc.timestamp}</p>
                  </div>
                </div>
                
                {/* Step-by-step breakdown */}
                {calc.steps.length > 0 && (
                  <div className="mt-3 space-y-1">
                    <p className="text-sm font-medium text-gray-700">Steps:</p>
                    {calc.steps.map((step, index) => (
                      <div key={index} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="font-mono">{index + 1}.</span>
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {calculations.length > 0 && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setCalculations([])}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear history
            </button>
          </div>
        )}
      </div>

      <div className="bg-green-50 rounded-lg p-4">
        <p className="text-sm text-green-800">
          <strong>Try asking:</strong> "Calculate 15% tip on $85.50", "What's 2^10?", 
          "Solve (5 + 3) * 2 - 4", or "Calculate compound interest on $1000 at 5% for 3 years"
        </p>
      </div>
    </div>
  );
} 