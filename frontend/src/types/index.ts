export interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  timestamp: string;
  source_url: string;
}

export interface StocksResponse {
  last_updated: string | null;
  stocks: Stock[];
  count: number;
}

export interface EveningWrap {
  title: string;
  url: string;
  date: string;
  content: string;
  formatted_content?: string;
  images: string[];
  scraped_at: string;
  summary?: string;
  summary_generated_at?: string;
}

export interface EveningWrapListItem {
  date: string;
  title: string;
  filename: string;
}

export interface EveningWrapListResponse {
  articles: EveningWrapListItem[];
  count: number;
}

export interface StockHistoryPoint {
  date: string;
  close: number;
}

export interface StockHistoryItem {
  symbol: string;
  history: StockHistoryPoint[];
}

export interface StockHistoryResponse {
  last_updated: string | null;
  days: number;
  stocks: StockHistoryItem[];
  count: number;
}

export interface DailyPnLRecord {
  pnl: number;
  holdings: Record<string, number>;
  calculated_at: string;
}

export interface DailyPnLResponse {
  last_updated: string | null;
  records: Record<string, DailyPnLRecord>;
}

export interface HoldingsResponse {
  last_updated: string | null;
  holdings: Record<string, number>;
  purchase_prices: Record<string, number>;
}
