import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { StockHistoryItem } from '../types';

interface StockChartProps {
  historyData: StockHistoryItem[];
  lastUpdated: string | null;
}

const COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#14b8a6', // teal
  '#6366f1', // indigo
];

export default function StockChart({ historyData, lastUpdated }: StockChartProps) {
  if (!historyData || historyData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-2">Price History (10 Days)</h2>
        <p className="text-gray-500">No history data available. Run fetch_history.py to populate.</p>
      </div>
    );
  }

  // Transform data for Recharts - need all stocks on same date points
  const dates = historyData[0]?.history.map((h) => h.date) || [];
  const chartData = dates.map((date) => {
    const point: Record<string, string | number> = { date: date.slice(5) }; // MM-DD format
    historyData.forEach((stock) => {
      const pricePoint = stock.history.find((h) => h.date === date);
      if (pricePoint) {
        point[stock.symbol.replace('.AX', '')] = pricePoint.close;
      }
    });
    return point;
  });

  const symbols = historyData.map((s) => s.symbol.replace('.AX', ''));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-gray-800">Price History (10 Days)</h2>
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </p>
        )}
      </div>

      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#6b7280" />
            <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
              }}
              formatter={(value: number | undefined) => [`$${(value ?? 0).toFixed(2)}`, '']}
            />
            <Legend />
            {symbols.map((symbol, index) => (
              <Line
                key={symbol}
                type="monotone"
                dataKey={symbol}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
