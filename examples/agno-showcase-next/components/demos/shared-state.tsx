"use client";

import React, { useState } from "react";
import { useCopilotAction, useCopilotReadable } from "@copilotkit/react-core";

interface TodoItem {
  id: string;
  text: string;
  completed: boolean;
}

export function SharedStateDemo() {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [filter, setFilter] = useState<"all" | "active" | "completed">("all");

  // Make the todos and filter readable to the agent
  useCopilotReadable({
    description: "Current todo list",
    value: todos,
  });

  useCopilotReadable({
    description: "Current filter setting",
    value: filter,
  });

  // Actions the agent can perform
  useCopilotAction({
    name: "add_todo",
    description: "Add a new todo item",
    parameters: [
      {
        name: "text",
        type: "string",
        description: "The text of the todo item",
      },
    ],
    handler: async ({ text }) => {
      const newTodo: TodoItem = {
        id: Date.now().toString(),
        text,
        completed: false,
      };
      setTodos((prev) => [...prev, newTodo]);
      return `Added todo: "${text}"`;
    },
  });

  useCopilotAction({
    name: "toggle_todo",
    description: "Toggle the completion status of a todo",
    parameters: [
      {
        name: "todoId",
        type: "string",
        description: "The ID of the todo to toggle",
      },
    ],
    handler: async ({ todoId }) => {
      setTodos((prev) =>
        prev.map((todo) =>
          todo.id === todoId ? { ...todo, completed: !todo.completed } : todo
        )
      );
      const todo = todos.find((t) => t.id === todoId);
      return `Toggled todo: "${todo?.text}"`;
    },
  });

  useCopilotAction({
    name: "delete_todo",
    description: "Delete a todo item",
    parameters: [
      {
        name: "todoId",
        type: "string",
        description: "The ID of the todo to delete",
      },
    ],
    handler: async ({ todoId }) => {
      const todo = todos.find((t) => t.id === todoId);
      setTodos((prev) => prev.filter((t) => t.id !== todoId));
      return `Deleted todo: "${todo?.text}"`;
    },
  });

  useCopilotAction({
    name: "set_filter",
    description: "Change the todo list filter",
    parameters: [
      {
        name: "filterType",
        type: "string",
        description: "Filter type: 'all', 'active', or 'completed'",
      },
    ],
    handler: async ({ filterType }) => {
      if (["all", "active", "completed"].includes(filterType)) {
        setFilter(filterType as typeof filter);
        return `Filter set to: ${filterType}`;
      }
      return "Invalid filter type";
    },
  });

  const filteredTodos = todos.filter((todo) => {
    if (filter === "active") return !todo.completed;
    if (filter === "completed") return todo.completed;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Shared Todo List</h2>
        
        {/* Filter buttons */}
        <div className="flex gap-2 mb-4">
          {(["all", "active", "completed"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-md capitalize ${
                filter === f
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 hover:bg-gray-300"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Todo list */}
        {filteredTodos.length === 0 ? (
          <p className="text-gray-500">
            {filter === "all"
              ? "No todos yet. Ask the agent to add some!"
              : `No ${filter} todos.`}
          </p>
        ) : (
          <ul className="space-y-2">
            {filteredTodos.map((todo) => (
              <li
                key={todo.id}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <input
                  type="checkbox"
                  checked={todo.completed}
                  onChange={() => {
                    setTodos((prev) =>
                      prev.map((t) =>
                        t.id === todo.id ? { ...t, completed: !t.completed } : t
                      )
                    );
                  }}
                  className="w-5 h-5"
                />
                <span
                  className={`flex-1 ${
                    todo.completed ? "line-through text-gray-500" : ""
                  }`}
                >
                  {todo.text}
                </span>
                <button
                  onClick={() => setTodos((prev) => prev.filter((t) => t.id !== todo.id))}
                  className="text-red-500 hover:text-red-700"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Stats */}
        <div className="mt-4 text-sm text-gray-600">
          {todos.length} total, {todos.filter((t) => !t.completed).length} active,{" "}
          {todos.filter((t) => t.completed).length} completed
        </div>
      </div>

      <div className="bg-blue-50 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Try asking:</strong> "Add a todo to buy groceries", "Mark the first todo as done", 
          "Show only active todos", or "Delete all completed todos"
        </p>
      </div>
    </div>
  );
} 