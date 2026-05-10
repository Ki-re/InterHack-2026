import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type AgentContextValue = {
  selectedAgentId: number | null;
  setSelectedAgentId: (id: number | null) => void;
};

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [selectedAgentId, setSelectedAgentIdState] = useState<number | null>(null);

  const setSelectedAgentId = useCallback((id: number | null) => {
    setSelectedAgentIdState(id);
  }, []);

  return (
    <AgentContext.Provider value={{ selectedAgentId, setSelectedAgentId }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error("useAgent must be used within AgentProvider");
  return ctx;
}
