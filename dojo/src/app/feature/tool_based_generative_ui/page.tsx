"use client";
import { CopilotKit, useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { useState, useEffect } from "react";
import "@copilotkit/react-ui/styles.css";
import "./style.css";

export default function AgenticChat() {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      showDevConsole={false}
      // agent lock to the relevant agent
      agent="toolBasedGenerativeUIAgent"
    >
      <div
        className="min-h-full w-full flex items-center justify-center"
        style={
          {
            // "--copilot-kit-primary-color": "#222",
            // "--copilot-kit-separator-color": "#CCC",
          } as CopilotKitCSSProperties
        }
      >
        <Haiku />
        <CopilotSidebar
          defaultOpen={true}
          labels={{
            title: "Haiku Generator",
            initial: "I'm a haiku generator 👋. How can I help you?",
          }}
          clickOutsideToClose={false}
        />
      </div>
    </CopilotKit>
  );
}

function Haiku() {
  const [haiku, setHaiku] = useState<{
    japanese: string[];
    english: string[];
  }>({
    japanese: ["仮の句よ", "まっさらながら", "花を呼ぶ"],
    english: [
      "A placeholder verse—",
      "even in a blank canvas,",
      "it beckons flowers.",
    ],
  });

  // Track if we've already updated for this haiku to avoid duplicate updates
  const [lastUpdatedHaiku, setLastUpdatedHaiku] = useState<string>("");

  useCopilotAction({
    name: "generate_haiku",
    parameters: [
      {
        name: "japanese",
        type: "string[]",
      },
      {
        name: "english",
        type: "string[]",
      },
    ],
    followUp: false,
    handler: async (args: { japanese: string[]; english: string[] }) => {
      console.log("Handler received args:", args);
      
      if (args.japanese && args.english) {
        console.log("Setting haiku from handler:", { japanese: args.japanese, english: args.english });
        setHaiku({ japanese: args.japanese, english: args.english });
        setLastUpdatedHaiku(JSON.stringify(args));
        return "Haiku generated and displayed.";
      } else {
        console.error("Missing japanese or english in args:", args);
        return "Error: Could not extract haiku data.";
      }
    },
    render: ({ args: generatedHaiku, result, status }) => {
      console.log("Render called with:", { generatedHaiku, result, status });
      
      // Update the haiku when we receive it, regardless of status
      if (generatedHaiku?.japanese && generatedHaiku?.english) {
        const haikuString = JSON.stringify(generatedHaiku);
        if (haikuString !== lastUpdatedHaiku) {
          console.log("Setting haiku from render:", generatedHaiku);
          setHaiku({ japanese: generatedHaiku.japanese, english: generatedHaiku.english });
          setLastUpdatedHaiku(haikuString);
        }
      }
      
      // Return empty fragment to not show haiku in the sidebar
      return <></>;
    },
  });
  
  return (
    <>
      <div className="text-left">
        {haiku?.japanese.map((line, index) => (
          <div className="flex items-center gap-6 mb-2" key={index}>
            <p className="text-4xl font-bold text-gray-500">{line}</p>
            <p className="text-base font-light">{haiku?.english?.[index]}</p>
          </div>
        ))}
      </div>
    </>
  );
}
