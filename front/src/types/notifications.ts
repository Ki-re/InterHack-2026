export type Notification = {
  id: number;
  agent_id: number | null;
  alert_id: string;
  title: string;
  body: string;
  created_at: string;
  read_at: string | null;
};
