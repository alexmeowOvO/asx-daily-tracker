import { useState, useEffect, useCallback } from 'react';
import { StockTable } from './components/StockTable';
import { EveningWrap } from './components/EveningWrap';
import type {
  StocksResponse,
  EveningWrap as EveningWrapType,
  EveningWrapListItem,
  StockHistoryResponse,
  DailyPnLResponse,
} from './types';

// Static mode: when deployed (production build), read from static JSON files
const isStatic = import.meta.env.PROD;

function App() {
  const [stocks, setStocks] = useState<StocksResponse | null>(null);
  const [eveningWrap, setEveningWrap] = useState<EveningWrapType | null>(null);
  const [eveningWrapList, setEveningWrapList] = useState<EveningWrapListItem[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [stockHistory, setStockHistory] = useState<StockHistoryResponse | null>(null);
  const [myStocks, setMyStocks] = useState<StocksResponse | null>(null);
  const [myStockHistory, setMyStockHistory] = useState<StockHistoryResponse | null>(null);
  const [holdings, setHoldings] = useState<Record<string, number>>({});
  const [purchasePrices, setPurchasePrices] = useState<Record<string, number>>({});
  const [dailyPnL, setDailyPnL] = useState<DailyPnLResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [wrapLoading, setWrapLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch article by date
  const fetchArticleByDate = useCallback(async (date: string) => {
    setWrapLoading(true);
    try {
      const dateClean = date.replace(/-/g, '');
      const url = isStatic
        ? `/data/evening_wrap_${dateClean}.json`
        : `/api/evening-wrap/${date}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEveningWrap(data);
        setSelectedDate(date);
      }
    } catch (err) {
      console.error('Error fetching article:', err);
    } finally {
      setWrapLoading(false);
    }
  }, []);

  // Save holdings and purchase prices to server (disabled in static/deployed mode)
  const saveHoldingsData = useCallback(async (
    newHoldings: Record<string, number>,
    newPurchasePrices: Record<string, number>
  ) => {
    if (isStatic) return; // Read-only in deployed mode
    try {
      await fetch('/api/my-holdings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          holdings: newHoldings,
          purchase_prices: newPurchasePrices,
        }),
      });
    } catch (err) {
      console.error('Error saving holdings:', err);
    }
  }, []);

  // Handle holding change
  const handleHoldingChange = useCallback((symbol: string, shares: number) => {
    setHoldings(prev => {
      const newHoldings = { ...prev, [symbol]: shares };
      saveHoldingsData(newHoldings, purchasePrices);
      return newHoldings;
    });
  }, [saveHoldingsData, purchasePrices]);

  // Handle purchase price change
  const handlePurchasePriceChange = useCallback((symbol: string, price: number) => {
    setPurchasePrices(prev => {
      const newPrices = { ...prev, [symbol]: price };
      saveHoldingsData(holdings, newPrices);
      return newPrices;
    });
  }, [saveHoldingsData, holdings]);

  // Initial data fetch
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [stocksRes, wrapListRes, historyRes, myStocksRes, myHistoryRes, holdingsRes, dailyPnLRes] = await Promise.all(
          isStatic
            ? [
                fetch('/data/stocks.json'),
                fetch('/data/evening_wrap_index.json'),
                fetch('/data/stocks_history_10d.json'),
                fetch('/data/my_stocks.json'),
                fetch('/data/my_stocks_history_10d.json'),
                fetch('/data/my_holdings.json'),
                fetch('/data/daily_pnl.json'),
              ]
            : [
                fetch('/api/stocks'),
                fetch('/api/evening-wrap/list'),
                fetch('/api/stocks-history'),
                fetch('/api/my-stocks'),
                fetch('/api/my-stocks-history'),
                fetch('/api/my-holdings'),
                fetch('/api/daily-pnl'),
              ]
        );

        if (stocksRes.ok) {
          const stocksData = await stocksRes.json();
          setStocks(stocksData);
        }

        if (wrapListRes.ok) {
          const listData = await wrapListRes.json();
          setEveningWrapList(listData.articles || []);

          // Auto-select the latest article
          if (listData.articles && listData.articles.length > 0) {
            const latestFilename = listData.articles[0].filename;
            const latestDate = latestFilename.replace('evening_wrap_', '').replace('.json', '');
            fetchArticleByDate(latestDate);
          }
        }

        if (historyRes.ok) {
          const historyData = await historyRes.json();
          setStockHistory(historyData);
        }

        if (myStocksRes.ok) {
          const myStocksData = await myStocksRes.json();
          setMyStocks(myStocksData);
        }

        if (myHistoryRes.ok) {
          const myHistoryData = await myHistoryRes.json();
          setMyStockHistory(myHistoryData);
        }

        if (holdingsRes.ok) {
          const holdingsData = await holdingsRes.json();
          setHoldings(holdingsData.holdings || {});
          setPurchasePrices(holdingsData.purchase_prices || {});
        }

        if (dailyPnLRes.ok) {
          const pnlData = await dailyPnLRes.json();
          setDailyPnL(pnlData);
        }
      } catch (err) {
        setError(isStatic
          ? 'Failed to load data. The data files may be missing.'
          : 'Failed to fetch data. Make sure the API server is running.');
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [fetchArticleByDate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-800 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg max-w-md">
          <h2 className="font-bold mb-2">Error</h2>
          <p>{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-gray-800 text-white shadow-lg">
        <div className="max-w-[2048px] mx-auto px-2 sm:px-3 py-6">
          <h1 className="text-2xl font-bold">ASX Stock Tracker</h1>
          <p className="text-gray-300 text-sm mt-1">
            Track Australian stocks and market updates
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[2048px] mx-auto px-2 sm:px-3 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-10 gap-4 lg:gap-6">
          {/* Stocks Section */}
          <div className="lg:col-span-3 space-y-4">
            {/* My Stocks - on top */}
            {myStocks && myStocks.stocks && myStocks.stocks.length > 0 && (
              <StockTable
                stocks={myStocks.stocks}
                lastUpdated={myStocks.last_updated || null}
                history={myStockHistory?.stocks || []}
                title="My Stocks"
                showHoldings={true}
                holdings={holdings}
                purchasePrices={purchasePrices}
                onHoldingChange={handleHoldingChange}
                onPurchasePriceChange={handlePurchasePriceChange}
              />
            )}

            <StockTable
              stocks={stocks?.stocks || []}
              lastUpdated={stocks?.last_updated || null}
              history={stockHistory?.stocks || []}
              title="Popular Stocks"
            />
          </div>

          {/* Evening Wrap Section */}
          <div className="lg:col-span-7 lg:max-h-[calc(200vh-180px)] flex flex-col min-h-0">
            <EveningWrap
              article={eveningWrap}
              articleList={eveningWrapList}
              selectedDate={selectedDate}
              onSelectDate={fetchArticleByDate}
              loading={wrapLoading}
              dailyPnL={dailyPnL}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-gray-400 text-center py-4 mt-8">
        <p className="text-sm">
          Data from Yahoo Finance and Market Index
        </p>
      </footer>
    </div>
  );
}

export default App;
