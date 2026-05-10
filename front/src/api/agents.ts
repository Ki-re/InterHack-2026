import { apiRequest } from "@/api/client";

export type Agent = {
  id: number;
  name: string;
  email: string;
  zone: "north" | "east" | "south" | "canary" | "balearic";
  managerId: number;
};

export async function fetchAgents(): Promise<Agent[]> {
  return apiRequest<Agent[]>("/agents");
}
