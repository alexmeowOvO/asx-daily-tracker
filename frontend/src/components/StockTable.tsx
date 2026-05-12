import { Fragment } from 'react';
import type { Stock, StockHistoryItem } from '../types';

interface StockTableProps {
  stocks: Stock[];
  lastUpdated: string | null;
  history: StockHistoryItem[];
  title?: string;
  showHoldings?: boolean;
  holdings?: Record<string, number>;
  purchasePrices?: Record<string, number>;
  onHoldingChange?: (symbol: string, shares: number) => void;
  onPurchasePriceChange?: (symbol: string, price: number) => void;
}

export function StockTable({
  stocks,
  lastUpdated,
  history,
  title = "ASX Stocks",
  showHoldings = false,
  holdings = {},
  purchasePrices = {},
  onHoldingChange,
  onPurchasePriceChange,
}: StockTableProps) {
  const historyBySymbol = new Map(
    history.map((item) => [item.symbol, item.history]),
  );

  const formatPrice = (price: number) => {
    return price.toLocaleString('en-AU', {
      style: 'currency',
      currency: 'AUD',
    });
  };

  const formatChange = (change: number) => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}`;
  };

  const formatPercent = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const formatDate = (isoString: string | null) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString('en-AU', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const buildSparklineData = (values: number[], dates: string[], width = 320, height = 60) => {
    if (values.length < 2) return { path: '', points: [] };
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const paddingX = 25;
    const paddingY = 12;
    const stepX = (width - paddingX * 2) / (values.length - 1);

    const points: { x: number; y: number; price: number; date: string }[] = [];
    const pathParts: string[] = [];

    values.forEach((value, index) => {
      const x = paddingX + index * stepX;
      const y = paddingY + ((max - value) / range) * (height - paddingY * 2);
      points.push({ x, y, price: value, date: dates[index] || '' });
      pathParts.push(`${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`);
    });

    return { path: pathParts.join(' '), points };
  };

  // Calculate totals for holdings
  const { totalDailyPnL, totalCost, totalValue, totalPnL } = showHoldings
    ? stocks.reduce((acc, stock) => {
        const shares = holdings[stock.symbol] || 0;
        const buyPrice = purchasePrices[stock.symbol] || 0;
        const cost = shares * buyPrice;
        const value = shares * stock.price;
        const dailyPnL = shares * stock.change;
        const pnl = value - cost;

        return {
          totalDailyPnL: acc.totalDailyPnL + dailyPnL,
          totalCost: acc.totalCost + cost,
          totalValue: acc.totalValue + value,
          totalPnL: acc.totalPnL + (buyPrice > 0 ? pnl : 0),
        };
      }, { totalDailyPnL: 0, totalCost: 0, totalValue: 0, totalPnL: 0 })
    : { totalDailyPnL: 0, totalCost: 0, totalValue: 0, totalPnL: 0 };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="bg-gray-800 text-white px-4 py-3">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-gray-300">
          Last updated: {formatDate(lastUpdated)}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Symbol
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Change
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                % Change
              </th>
                          </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {stocks.map((stock) => {
              const series = historyBySymbol.get(stock.symbol) || [];
              const values = series.map((point) => point.close);
              const dates = series.map((point) => point.date);
              const trendUp =
                values.length > 1 && values[values.length - 1] >= values[0];
              const { path: sparkPath, points } = buildSparklineData(values, dates);
              const lineColor = trendUp ? '#16a34a' : '#dc2626';

              const shares = holdings[stock.symbol] || 0;
              const buyPrice = purchasePrices[stock.symbol] || 0;
              const cost = shares * buyPrice;
              const currentValue = shares * stock.price;
              const stockTotalPnL = currentValue - cost;
              const dailyPnL = shares * stock.change;

              return (
                <Fragment key={stock.symbol}>
                  <tr className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <a
                        href={stock.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {stock.symbol.replace('.AX', '')}
                      </a>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-700">
                      {stock.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right font-medium">
                      {formatPrice(stock.price)}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${
                        stock.change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {formatChange(stock.change)}
                    </td>
                    <td
                      className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${
                        stock.change_percent >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {formatPercent(stock.change_percent)}
                    </td>
                    </tr>
                  {/* Holdings row - only for My Stocks */}
                  {showHoldings && (
                    <tr className="bg-blue-50/50">
                      <td colSpan={5} className="px-4 py-2">
                        <div className="flex flex-wrap items-center gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500">Shares:</span>
                            <input
                              type="number"
                              min="0"
                              value={shares || ''}
                              onChange={(e) => onHoldingChange?.(stock.symbol, parseInt(e.target.value) || 0)}
                              placeholder="0"
                              className="w-20 px-2 py-1 text-sm text-right border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500">Buy @</span>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={buyPrice || ''}
                              onChange={(e) => onPurchasePriceChange?.(stock.symbol, parseFloat(e.target.value) || 0)}
                              placeholder="0.00"
                              className="w-20 px-2 py-1 text-sm text-right border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          {shares > 0 && buyPrice > 0 && (
                            <div className="flex items-center gap-2">
                              <span className="text-gray-500">Total P&L:</span>
                              <span className={`font-medium ${stockTotalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {stockTotalPnL >= 0 ? '+' : ''}{formatPrice(stockTotalPnL)}
                              </span>
                            </div>
                          )}
                          {shares > 0 && (
                            <div className="flex items-center gap-2">
                              <span className="text-gray-500">Today:</span>
                              <span className={`font-medium ${dailyPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {dailyPnL >= 0 ? '+' : ''}{formatPrice(dailyPnL)}
                              </span>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                  <tr className="bg-gray-50/50">
                    <td colSpan={5} className="px-4 pb-3 pt-1">
                      {values.length >= 2 ? (
                        <div className="flex items-center gap-3">
                          <svg
                            viewBox="0 0 320 60"
                            className="h-16 w-full max-w-[400px]"
                            aria-label="Last 10 trading days"
                          >
                            <path
                              d={sparkPath}
                              fill="none"
                              stroke={lineColor}
                              strokeWidth="2.5"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                            {points.map((point, idx) => (
                              <g key={idx}>
                                <circle
                                  cx={point.x}
                                  cy={point.y}
                                  r="3.5"
                                  fill={lineColor}
                                  stroke="white"
                                  strokeWidth="1.5"
                                />
                                <text
                                  x={point.x}
                                  y={point.y - 8}
                                  textAnchor="middle"
                                  fontSize="7"
                                  fill="#374151"
                                >
                                  {point.price.toFixed(0)}
                                </text>
                                <title>
                                  {point.date}: ${point.price.toFixed(2)}
                                </title>
                              </g>
                            ))}
                          </svg>
                          <span className="text-xs text-gray-500">
                            Last {values.length} days
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">
                          No history available
                        </span>
                      )}
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Total P&L Summary */}
      {showHoldings && stocks.length > 0 && (
        <div className="px-4 py-3 border-t bg-gray-50 space-y-2">
          {totalCost > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Total Cost</span>
              <span className="font-medium text-gray-700">{formatPrice(totalCost)}</span>
            </div>
          )}
          {totalCost > 0 && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-600">Current Value</span>
              <span className="font-medium text-gray-700">{formatPrice(totalValue)}</span>
            </div>
          )}
          {totalCost > 0 && (
            <div className={`flex justify-between items-center pt-2 border-t`}>
              <span className="font-semibold text-gray-700">Total P&L</span>
              <span className={`text-lg font-bold ${totalPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {totalPnL >= 0 ? '+' : ''}{formatPrice(totalPnL)}
                <span className="text-sm ml-1">
                  ({totalCost > 0 ? ((totalPnL / totalCost) * 100).toFixed(1) : 0}%)
                </span>
              </span>
            </div>
          )}
          <div className={`flex justify-between items-center ${totalCost > 0 ? 'pt-2 border-t' : ''}`}>
            <span className="font-semibold text-gray-700">Today's P&L</span>
            <span className={`text-lg font-bold ${totalDailyPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {totalDailyPnL >= 0 ? '+' : ''}{formatPrice(totalDailyPnL)}
            </span>
          </div>
        </div>
      )}

      {stocks.length === 0 && (
        <div className="px-4 py-8 text-center text-gray-500">
          No stock data available
        </div>
      )}
    </div>
  );
}
