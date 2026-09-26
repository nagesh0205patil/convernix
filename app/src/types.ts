export type User = {
  id: number; username: string; email: string; first_name: string; last_name: string;
  team_name: string; role: 'viewer' | 'editor' | 'admin' | 'owner'; organization: string;
};
export type Tokens = { access: string; refresh: string };
export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type Enquiry = {
  id: number; reference: string; customer_name: string; phone_number: string; customer_email: string;
  organization_name: string; team_name: string; message: string; status: string; created_at: string;
};
export type Message = { id: number; direction: 'incoming' | 'outgoing'; content: string; status: string; timestamp: string };
export type Conversation = Enquiry & { last_message: string; last_message_at: string; unread_count: number; messages?: Message[] };
export type Campaign = { id: number; name: string; message: string; target_audience: string; status: string; scheduled_at: string | null; sent_count: number; delivered_count: number; opened_count: number; clicked_count: number };
export type Dashboard = { totals: { enquiries: number; campaigns: number; sent: number; delivered: number; opened: number; clicked: number } };
