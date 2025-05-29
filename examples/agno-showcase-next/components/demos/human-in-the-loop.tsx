"use client";

import React, { useState } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface WeatherQuery {
  id: string;
  city: string;
  temperature: number;
  condition: string;
  humidity: number;
  windSpeed: number;
  timestamp: string;
  userConfirmed: boolean;
}

export function HumanInTheLoopDemo() {
  const [weatherQueries, setWeatherQueries] = useState<WeatherQuery[]>([]);
  const [pendingConfirmation, setPendingConfirmation] = useState<WeatherQuery | null>(null);

  // Make weather data readable to the agent
  useCopilotReadable({
    description: "Weather query history",
    value: weatherQueries,
  });

  // Action to request weather data (requires confirmation)
  useCopilotAction({
    name: "request_weather",
    description: "Request weather data for a city (requires user confirmation)",
    parameters: [
      {
        name: "city",
        type: "string",
        description: "City name to get weather for",
      },
      {
        name: "temperature",
        type: "number",
        description: "Temperature in Celsius",
      },
      {
        name: "condition",
        type: "string",
        description: "Weather condition (e.g., sunny, cloudy, rainy)",
      },
      {
        name: "humidity",
        type: "number",
        description: "Humidity percentage",
      },
      {
        name: "windSpeed",
        type: "number",
        description: "Wind speed in km/h",
      },
    ],
    handler: async ({ city, temperature, condition, humidity, windSpeed }) => {
      const query: WeatherQuery = {
        id: Date.now().toString(),
        city,
        temperature,
        condition,
        humidity,
        windSpeed,
        timestamp: new Date().toLocaleTimeString(),
        userConfirmed: false,
      };
      
      setPendingConfirmation(query);
      return `Weather data for ${city} is ready. Please confirm to display.`;
    },
  });

  const confirmWeatherData = () => {
    if (pendingConfirmation) {
      setWeatherQueries((prev) => [
        { ...pendingConfirmation, userConfirmed: true },
        ...prev,
      ]);
      setPendingConfirmation(null);
    }
  };

  const rejectWeatherData = () => {
    setPendingConfirmation(null);
  };

  return (
    <div className="space-y-6">
      {/* Confirmation dialog */}
      {pendingConfirmation && (
        <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-4">
          <h3 className="font-semibold text-yellow-900 mb-2">
            Confirm Weather Data Request
          </h3>
          <p className="text-yellow-800 mb-3">
            The agent wants to show weather data for {pendingConfirmation.city}:
          </p>
          <div className="bg-white rounded p-3 mb-3">
            <p>🌡️ Temperature: {pendingConfirmation.temperature}°C</p>
            <p>☁️ Condition: {pendingConfirmation.condition}</p>
            <p>💧 Humidity: {pendingConfirmation.humidity}%</p>
            <p>💨 Wind: {pendingConfirmation.windSpeed} km/h</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={confirmWeatherData}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Confirm
            </button>
            <button
              onClick={rejectWeatherData}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Weather Assistant</h2>
        
        {weatherQueries.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">No weather queries yet.</p>
            <p className="text-sm text-gray-400 mt-2">
              Ask the agent about weather in any city!
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {weatherQueries.map((query) => (
              <div
                key={query.id}
                className="border rounded-lg p-4 bg-gradient-to-r from-blue-50 to-cyan-50"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg">{query.city}</h3>
                  <span className="text-sm text-gray-500">{query.timestamp}</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-2xl">🌡️</span>
                    <span className="ml-2">{query.temperature}°C</span>
                  </div>
                  <div>
                    <span className="text-2xl">☁️</span>
                    <span className="ml-2">{query.condition}</span>
                  </div>
                  <div>
                    <span className="text-2xl">💧</span>
                    <span className="ml-2">{query.humidity}%</span>
                  </div>
                  <div>
                    <span className="text-2xl">💨</span>
                    <span className="ml-2">{query.windSpeed} km/h</span>
                  </div>
                </div>
                {query.userConfirmed && (
                  <div className="mt-2 text-xs text-green-600">
                    ✓ User confirmed
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-orange-50 rounded-lg p-4">
        <p className="text-sm text-orange-800">
          <strong>Try asking:</strong> "What's the weather in Tokyo?", 
          "Show me weather for Paris", or "Check the weather in New York"
        </p>
        <p className="text-xs text-orange-700 mt-2">
          Note: Weather requests require your confirmation before displaying!
        </p>
      </div>
    </div>
  );
} 