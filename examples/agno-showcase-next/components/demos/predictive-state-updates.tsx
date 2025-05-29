"use client";

import React, { useState } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface FormData {
  name: string;
  email: string;
  company: string;
  role: string;
  message: string;
}

interface Prediction {
  field: keyof FormData;
  suggestedValue: string;
  confidence: number;
  reasoning: string;
}

export function PredictiveStateUpdatesDemo() {
  const [formData, setFormData] = useState<FormData>({
    name: "",
    email: "",
    company: "",
    role: "",
    message: "",
  });
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [showPredictions, setShowPredictions] = useState(true);

  // Make form data readable to the agent
  useCopilotReadable({
    description: "Current form data",
    value: formData,
  });

  // Action to predict form fields
  useCopilotAction({
    name: "predict_form_field",
    description: "Predict and suggest values for form fields based on context",
    parameters: [
      {
        name: "field",
        type: "string",
        description: "The form field to predict (name, email, company, role, message)",
      },
      {
        name: "suggestedValue",
        type: "string",
        description: "The predicted value for the field",
      },
      {
        name: "confidence",
        type: "number",
        description: "Confidence level (0-100)",
      },
      {
        name: "reasoning",
        type: "string",
        description: "Explanation for the prediction",
      },
    ],
    handler: async ({ field, suggestedValue, confidence, reasoning }) => {
      const prediction: Prediction = {
        field: field as keyof FormData,
        suggestedValue,
        confidence,
        reasoning,
      };
      
      setPredictions((prev) => {
        const filtered = prev.filter((p) => p.field !== field);
        return [...filtered, prediction];
      });
      
      return `Predicted ${field}: "${suggestedValue}" (${confidence}% confidence)`;
    },
  });

  // Action to apply a prediction
  useCopilotAction({
    name: "apply_prediction",
    description: "Apply a predicted value to a form field",
    parameters: [
      {
        name: "field",
        type: "string",
        description: "The form field to update",
      },
      {
        name: "value",
        type: "string",
        description: "The value to apply",
      },
    ],
    handler: async ({ field, value }) => {
      setFormData((prev) => ({
        ...prev,
        [field]: value,
      }));
      
      // Remove the applied prediction
      setPredictions((prev) => prev.filter((p) => p.field !== field));
      
      return `Applied "${value}" to ${field}`;
    },
  });

  const applyPrediction = (prediction: Prediction) => {
    setFormData((prev) => ({
      ...prev,
      [prediction.field]: prediction.suggestedValue,
    }));
    setPredictions((prev) => prev.filter((p) => p.field !== prediction.field));
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Smart Contact Form</h2>
        
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company
            </label>
            <input
              type="text"
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your company"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Role
            </label>
            <input
              type="text"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your role"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Message
            </label>
            <textarea
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
              placeholder="Your message..."
            />
          </div>
        </form>

        {/* Predictions panel */}
        {showPredictions && predictions.length > 0 && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-medium text-blue-900 mb-3">AI Suggestions</h3>
            <div className="space-y-2">
              {predictions.map((prediction) => (
                <div
                  key={prediction.field}
                  className="bg-white p-3 rounded border border-blue-200"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className="font-medium capitalize">{prediction.field}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        "{prediction.suggestedValue}"
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {prediction.reasoning} ({prediction.confidence}% confidence)
                      </p>
                    </div>
                    <button
                      onClick={() => applyPrediction(prediction)}
                      className="ml-3 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      Apply
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 flex items-center">
          <input
            type="checkbox"
            id="showPredictions"
            checked={showPredictions}
            onChange={(e) => setShowPredictions(e.target.checked)}
            className="mr-2"
          />
          <label htmlFor="showPredictions" className="text-sm text-gray-700">
            Show AI predictions
          </label>
        </div>
      </div>

      <div className="bg-purple-50 rounded-lg p-4">
        <p className="text-sm text-purple-800">
          <strong>Try:</strong> Start filling the form and ask "Can you help me complete this form?" 
          or "Predict what I should write in the message field"
        </p>
        <p className="text-xs text-purple-700 mt-2">
          The AI will analyze your inputs and suggest contextual completions!
        </p>
      </div>
    </div>
  );
} 