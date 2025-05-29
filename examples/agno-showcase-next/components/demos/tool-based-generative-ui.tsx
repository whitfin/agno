"use client";

import React, { useState } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface Haiku {
  id: string;
  title: string;
  lines: [string, string, string];
  theme: string;
  mood: "peaceful" | "energetic" | "melancholic" | "joyful";
  timestamp: string;
}

const moodColors = {
  peaceful: "bg-blue-100 border-blue-300 text-blue-900",
  energetic: "bg-orange-100 border-orange-300 text-orange-900",
  melancholic: "bg-purple-100 border-purple-300 text-purple-900",
  joyful: "bg-yellow-100 border-yellow-300 text-yellow-900",
};

const moodEmojis = {
  peaceful: "🌊",
  energetic: "⚡",
  melancholic: "🌙",
  joyful: "☀️",
};

export function ToolBasedGenerativeUIDemo() {
  const [haikus, setHaikus] = useState<Haiku[]>([]);
  const [selectedTheme, setSelectedTheme] = useState<string>("nature");

  // Make haikus readable to the agent
  useCopilotReadable({
    description: "Generated haikus collection",
    value: haikus,
  });

  // Tool for generating haikus
  useCopilotAction({
    name: "generate_haiku",
    description: "Generate a new haiku with a specific theme and mood",
    parameters: [
      {
        name: "title",
        type: "string",
        description: "Title for the haiku",
      },
      {
        name: "theme",
        type: "string",
        description: "Theme of the haiku (e.g., nature, technology, love, seasons)",
      },
      {
        name: "mood",
        type: "string",
        description: "Mood: peaceful, energetic, melancholic, or joyful",
      },
      {
        name: "line1",
        type: "string",
        description: "First line of the haiku (5 syllables)",
      },
      {
        name: "line2",
        type: "string",
        description: "Second line of the haiku (7 syllables)",
      },
      {
        name: "line3",
        type: "string",
        description: "Third line of the haiku (5 syllables)",
      },
    ],
    handler: async ({ title, theme, mood, line1, line2, line3 }) => {
      const newHaiku: Haiku = {
        id: Date.now().toString(),
        title,
        lines: [line1, line2, line3],
        theme,
        mood: mood as Haiku["mood"],
        timestamp: new Date().toLocaleTimeString(),
      };
      setHaikus((prev) => [newHaiku, ...prev]);
      return `Created haiku: "${title}"`;
    },
  });

  // Tool for clearing haikus
  useCopilotAction({
    name: "clear_haikus",
    description: "Clear all generated haikus",
    parameters: [],
    handler: async () => {
      setHaikus([]);
      return "All haikus cleared";
    },
  });

  // Tool for deleting a specific haiku
  useCopilotAction({
    name: "delete_haiku",
    description: "Delete a specific haiku by its ID",
    parameters: [
      {
        name: "haikuId",
        type: "string",
        description: "ID of the haiku to delete",
      },
    ],
    handler: async ({ haikuId }) => {
      const haiku = haikus.find((h) => h.id === haikuId);
      setHaikus((prev) => prev.filter((h) => h.id !== haikuId));
      return `Deleted haiku: "${haiku?.title}"`;
    },
  });

  const themes = ["nature", "technology", "love", "seasons", "city", "dreams"];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Haiku Generator</h2>
        
        {/* Theme selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Suggested Theme:
          </label>
          <div className="flex flex-wrap gap-2">
            {themes.map((theme) => (
              <button
                key={theme}
                onClick={() => setSelectedTheme(theme)}
                className={`px-3 py-1 rounded-full text-sm capitalize ${
                  selectedTheme === theme
                    ? "bg-indigo-500 text-white"
                    : "bg-gray-200 hover:bg-gray-300"
                }`}
              >
                {theme}
              </button>
            ))}
          </div>
        </div>

        {/* Haikus display */}
        {haikus.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-2">No haikus yet.</p>
            <p className="text-sm text-gray-400">
              Ask the agent to generate a haiku about {selectedTheme}!
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {haikus.map((haiku) => (
              <div
                key={haiku.id}
                className={`p-6 rounded-lg border-2 ${moodColors[haiku.mood]}`}
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-semibold text-lg flex items-center gap-2">
                      {haiku.title}
                      <span className="text-2xl">{moodEmojis[haiku.mood]}</span>
                    </h3>
                    <p className="text-sm opacity-75">
                      {haiku.theme} • {haiku.timestamp}
                    </p>
                  </div>
                  <button
                    onClick={() => setHaikus((prev) => prev.filter((h) => h.id !== haiku.id))}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    ×
                  </button>
                </div>
                <div className="space-y-1 font-serif italic">
                  {haiku.lines.map((line, index) => (
                    <p key={index} className="text-center">
                      {line}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {haikus.length > 0 && (
          <div className="mt-4 text-center">
            <button
              onClick={() => setHaikus([])}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear all haikus
            </button>
          </div>
        )}
      </div>

      <div className="bg-indigo-50 rounded-lg p-4">
        <p className="text-sm text-indigo-800">
          <strong>Try asking:</strong> "Write a peaceful haiku about {selectedTheme}", 
          "Create an energetic haiku about technology", or "Generate a melancholic haiku about autumn"
        </p>
      </div>
    </div>
  );
} 