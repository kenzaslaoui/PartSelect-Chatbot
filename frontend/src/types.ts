export interface Part {
  part_number: string;
  name: string;
  description: string;
  price?: number;
  compatible_models: string[];
}

export interface Blog {
  title: string;
  content: string;
  appliance_type?: string;
  url?: string;
}

export interface Repair {
  symptom: string;
  solution: string;
  appliance_type?: string;
  has_video: boolean;
  video_url?: string;
}

export interface ChatRequest {
  query: string;
}

export interface ChatResponse {
  response: string;
  parts: Part[];
  blogs: Blog[];
  repairs: Repair[];
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  parts?: Part[];
  blogs?: Blog[];
  repairs?: Repair[];
}
