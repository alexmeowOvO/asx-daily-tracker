import { useCallback, useEffect, useState } from 'react';
import type {
  DailyPnLResponse,
  EveningWrap,
  EveningWrapListItem,
  Stock,
  StockHistoryItem,
  StockHistoryResponse,
  StocksResponse,
} from './types';

const isStatic = import.meta.env.PROD;
const BASE = import.meta.env.BASE_URL;

const money = (value: number, digits = 2) => value.toLocaleString('en-AU', {
  style: 'currency',
  currency: 'AUD',
  minimumFractionDigits: digits,
  maximumFractionDigits: digits,
});

const cleanSymbol = (symbol: string) => symbol.replace('.AX', '');
const compactTitle = (title: string) => title.replace(/^Evening Wrap:\s*/i, '');
const isoFromFilename = (filename: string) => {
  const raw = filename.replace('evening_wrap_', '').replace('.json', '');
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
};
const fileDate = (date: string) => date.replace(/-/g, '');
const formatDate = (date: string, short = false) => new Date(`${date}T12:00:00`).toLocaleDateString('en-AU', short
  ? { day: 'numeric', month: 'long' }
  : { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

function summaryLines(article: EveningWrap | null) {
  if (!article) return [];
  if (article.summary) {
    return article.summary.split('\n').map((line) => line.replace(/^[*•\-\s]+/, '').trim()).filter(Boolean).slice(0, 3);
  }
  return article.content.split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 55 && !line.startsWith('[IMAGE:'))
    .slice(0, 3);
}

function sessionMood(item: EveningWrapListItem) {
  const title = item.title.toLowerCase();
  if (title.includes('gold') || title.includes('mining') || title.includes('miner')) return 'Resources set the pace';
  if (title.includes('bank')) return 'Banks steer the index';
  if (title.includes('energy') || title.includes('oil')) return 'Energy takes the lead';
  if (title.includes('healthcare')) return 'Healthcare in focus';
  if (title.includes('tech')) return 'Technology drives trade';
  return 'The close in review';
}

function trendValues(history: StockHistoryItem | undefined) {
  const values = history?.history.map((point) => point.close) ?? [];
  if (!values.length) return [36, 44, 41, 55, 50, 62, 68];
  const recent = values.slice(-7);
  const min = Math.min(...recent);
  const range = Math.max(...recent) - min || 1;
  return recent.map((value) => 22 + ((value - min) / range) * 58);
}

function Trend({ history, change }: { history?: StockHistoryItem; change: number }) {
  const bars = trendValues(history);
  return (
    <span className={`trend ${change >= 0 ? 'positive' : 'negative'}`} aria-label={`${change >= 0 ? 'Rising' : 'Falling'} recent trend`}>
      {bars.map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
    </span>
  );
}

function ReportPage({ article, onBack }: { article: EveningWrap; onBack: () => void }) {
  const paragraphs = article.content.split('\n').map((line) => line.trim()).filter(Boolean);
  return (
    <div className="report-page">
      <header className="report-nav">
        <button className="wordmark wordmark-button" onClick={onBack}>The <em>Closing</em> Ledger</button>
        <button className="back-link" onClick={onBack}>← Back to the close</button>
      </header>
      <main>
        <div className="report-page-meta"><span>Market report</span><time>{formatDate(article.date)}</time></div>
        <article className="report-article">
          <h1>{compactTitle(article.title)}</h1>
          <p className="report-intro">The complete market report for the Australian close, preserved in your daily archive.</p>
          <div className="report-byline"><span>Source · Market Index</span><span>Saved · {new Date(article.scraped_at).toLocaleString('en-AU')}</span><a href={article.url} target="_blank" rel="noreferrer">Original article ↗</a></div>
          {article.formatted_content ? (
            <div className="report-body" dangerouslySetInnerHTML={{ __html: article.formatted_content }} />
          ) : (
            <div className="report-body">
              {paragraphs.map((line, index) => {
                if (/^\[IMAGE:\d+\]$/.test(line)) return null;
                const header = line.length < 70 && !/[.!?]$/.test(line);
                return header ? <h2 key={index}>{line}</h2> : <p key={index}>{line}</p>;
              })}
            </div>
          )}
          <div className="report-footer-nav"><button onClick={onBack}>← Return to overview</button><a href={article.url} target="_blank" rel="noreferrer">Read at source ↗</a></div>
        </article>
      </main>
    </div>
  );
}

function App() {
  const [stocks, setStocks] = useState<StocksResponse | null>(null);
  const [myStocks, setMyStocks] = useState<StocksResponse | null>(null);
  const [history, setHistory] = useState<StockHistoryResponse | null>(null);
  const [myHistory, setMyHistory] = useState<StockHistoryResponse | null>(null);
  const [sessions, setSessions] = useState<EveningWrapListItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [article, setArticle] = useState<EveningWrap | null>(null);
  const [holdings, setHoldings] = useState<Record<string, number>>({});
  const [purchasePrices, setPurchasePrices] = useState<Record<string, number>>({});
  const [dailyPnL, setDailyPnL] = useState<DailyPnLResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [articleLoading, setArticleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [openPosition, setOpenPosition] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(() => new URLSearchParams(window.location.search).has('report'));

  const fetchArticle = useCallback(async (item: EveningWrapListItem, index: number, openReport = false) => {
    setArticleLoading(true);
    try {
      const date = fileDate(item.date || isoFromFilename(item.filename));
      const url = isStatic ? `${BASE}data/evening_wrap_${date}.json` : `/api/evening-wrap/${date}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Report unavailable');
      setArticle(await response.json());
      setSelectedIndex(index);
      setCalendarOpen(false);
      if (openReport) setReportOpen(true);
    } catch (err) {
      console.error('Error fetching report:', err);
    } finally {
      setArticleLoading(false);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const urls = isStatic ? [
          `${BASE}data/stocks.json`, `${BASE}data/evening_wrap_index.json`, `${BASE}data/stocks_history_10d.json`,
          `${BASE}data/my_stocks.json`, `${BASE}data/my_stocks_history_10d.json`, `${BASE}data/my_holdings.json`, `${BASE}data/daily_pnl.json`,
        ] : ['/api/stocks', '/api/evening-wrap/list', '/api/stocks-history', '/api/my-stocks', '/api/my-stocks-history', '/api/my-holdings', '/api/daily-pnl'];
        const responses = await Promise.all(urls.map((url) => fetch(url)));
        if (responses.some((response) => !response.ok)) throw new Error('One or more data sources failed');
        const [stockData, wrapData, historyData, myStockData, myHistoryData, holdingData, pnlData] = await Promise.all(responses.map((response) => response.json()));
        setStocks(stockData); setHistory(historyData); setMyStocks(myStockData); setMyHistory(myHistoryData);
        setHoldings(holdingData.holdings || {}); setPurchasePrices(holdingData.purchase_prices || {}); setDailyPnL(pnlData);
        const list: EveningWrapListItem[] = wrapData.articles || [];
        setSessions(list);
        if (list.length) {
          const reportDate = new URLSearchParams(window.location.search).get('report');
          const targetIndex = Math.max(0, reportDate ? list.findIndex((item) => fileDate(item.date) === reportDate) : 0);
          await fetchArticle(list[targetIndex], targetIndex);
        }
      } catch (err) {
        console.error(err);
        setError('The market data could not be loaded. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [fetchArticle]);

  useEffect(() => {
    const onPopState = () => setReportOpen(new URLSearchParams(window.location.search).has('report'));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const saveHoldings = useCallback(async (nextHoldings: Record<string, number>, nextPrices: Record<string, number>) => {
    if (isStatic) return;
    try {
      await fetch('/api/my-holdings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ holdings: nextHoldings, purchase_prices: nextPrices }) });
    } catch (err) { console.error('Error saving holdings:', err); }
  }, []);

  const updateHolding = (symbol: string, value: number) => {
    const next = { ...holdings, [symbol]: value };
    setHoldings(next); saveHoldings(next, purchasePrices);
  };
  const updatePrice = (symbol: string, value: number) => {
    const next = { ...purchasePrices, [symbol]: value };
    setPurchasePrices(next); saveHoldings(holdings, next);
  };

  const openReport = () => {
    if (!article) return;
    const url = new URL(window.location.href);
    url.searchParams.set('report', fileDate(article.date));
    window.history.pushState({}, '', url);
    setReportOpen(true);
    window.scrollTo(0, 0);
  };
  const closeReport = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('report');
    window.history.pushState({}, '', url);
    setReportOpen(false);
    window.scrollTo(0, 0);
  };

  const positions = myStocks?.stocks || [];
  const watchlist = stocks?.stocks || [];
  const currentSession = sessions[selectedIndex];
  const currentDate = article?.date || currentSession?.date || '';
  const portfolioValue = positions.reduce((sum, stock) => sum + (holdings[stock.symbol] || 0) * stock.price, 0);
  const liveReturn = positions.reduce((sum, stock) => sum + (holdings[stock.symbol] || 0) * stock.change, 0);
  const pnlRecords = Object.entries(dailyPnL?.records || {}).sort(([a], [b]) => b.localeCompare(a));
  const selectedPnlIndex = Math.max(0, pnlRecords.findIndex(([date]) => date <= currentDate));
  const currentPnl = pnlRecords[selectedPnlIndex]?.[1]?.pnl ?? liveReturn;
  const previousPnl = pnlRecords[selectedPnlIndex + 1]?.[1]?.pnl ?? 0;
  const latestValue = portfolioValue;
  const previousValue = latestValue - currentPnl;
  const advancing = watchlist.filter((stock) => stock.change_percent >= 0).length;
  const best = [...watchlist].sort((a, b) => b.change_percent - a.change_percent)[0];
  const weakest = [...watchlist].sort((a, b) => a.change_percent - b.change_percent)[0];
  const previousMoves = watchlist.map((stock) => {
    const item = history?.stocks.find((entry) => entry.symbol === stock.symbol);
    const values = item?.history.map((point) => point.close) || [];
    const change = values.length >= 3 ? ((values.at(-2)! - values.at(-3)!) / values.at(-3)!) * 100 : 0;
    return { stock, change };
  });
  const previousAdvancing = previousMoves.filter((item) => item.change >= 0).length;
  const previousBest = [...previousMoves].sort((a, b) => b.change - a.change)[0];
  const briefs = summaryLines(article);

  if (loading) return <div className="state-screen"><span className="loader" /><p>Preparing the closing ledger…</p></div>;
  if (error) return <div className="state-screen"><h1>The ledger is temporarily unavailable.</h1><p>{error}</p><button onClick={() => window.location.reload()}>Try again</button></div>;
  if (reportOpen && article) return <ReportPage article={article} onBack={closeReport} />;

  return (
    <div className="site-shell">
      <header className="site-header" id="top">
        <a className="wordmark" href="#top">The <em>Closing</em> Ledger</a>
        <nav aria-label="Primary navigation"><a href="#today">Today</a><a href="#portfolio">Portfolio</a><a href="#watchlist">Market watch</a><a href="#archive">Archive</a></nav>
        <div className="market-status"><i /><span>ASX data connected</span><button aria-label="Refresh market data" onClick={() => window.location.reload()}>↻</button></div>
      </header>

      <main>
        <section className="story" id="today">
          <div className="story-topline">
            <div><span>The day after the bell</span><time>{currentDate ? formatDate(currentDate) : 'Latest session'}</time></div>
            <div className="date-controls">
              <button aria-label="Newer session" disabled={selectedIndex === 0} onClick={() => fetchArticle(sessions[selectedIndex - 1], selectedIndex - 1)}>←</button>
              <button className="date-button" onClick={() => setCalendarOpen(!calendarOpen)}>{currentDate ? formatDate(currentDate, true) : 'Select date'} <small>⌄</small></button>
              <button aria-label="Older session" disabled={selectedIndex >= sessions.length - 1} onClick={() => fetchArticle(sessions[selectedIndex + 1], selectedIndex + 1)}>→</button>
            </div>
            {calendarOpen && <div className="calendar"><div className="calendar-heading"><strong>Report archive</strong><span>P&amp;L shown by session</span></div><div className="calendar-sessions">{sessions.slice(0, 12).map((session, index) => { const pnl = dailyPnL?.records[session.date]?.pnl; return <button className={index === selectedIndex ? 'selected' : ''} key={session.filename} onClick={() => fetchArticle(session, index)}><time>{formatDate(session.date, true)}</time><small className={(pnl ?? 0) >= 0 ? 'positive' : 'negative'}>{pnl == null ? 'Report' : `${pnl >= 0 ? '+' : ''}${money(pnl, 0)}`}</small></button>; })}</div></div>}
          </div>

          <div className="story-grid">
            <article>
              <h1>{article ? compactTitle(article.title) : 'The Australian market, after the bell.'}</h1>
              <p>{briefs[0] || 'Your personal view of the Australian close, portfolio movement and the market reports behind each session.'}</p>
              <div className="story-actions"><button onClick={openReport}>Read the full report →</button><a href="#portfolio">View your portfolio ↓</a></div>
            </article>
            <aside><span>The close in three lines</span><ol>{(briefs.length ? briefs : ['Market report loaded from your archive.', 'Portfolio performance is calculated from your holdings.', 'Watchlist prices show the latest collected market data.']).map((line, index) => <li key={index}><small>0{index + 1}</small><span>{line}</span></li>)}</ol></aside>
          </div>
        </section>

        <section className="metric-ledger" aria-label="Portfolio summary">
          <div className="metric-row current-row">
            <article className="featured-metric"><span>Latest close · Portfolio value</span><strong>{money(latestValue)}</strong><small>Across {Object.values(holdings).reduce((a, b) => a + b, 0).toLocaleString()} held shares</small></article>
            <article><span>Latest close · Return</span><strong className={currentPnl >= 0 ? 'positive' : 'negative'}>{currentPnl >= 0 ? '+' : ''}{money(currentPnl)}</strong><small>{currentDate ? formatDate(currentDate, true) : 'Latest session'}</small></article>
            <article><span>Latest close · Advancing</span><strong>{advancing} <i>of {watchlist.length}</i></strong><small>Watchlist breadth</small></article>
            <article><span>Latest close · Best</span><strong>{best ? cleanSymbol(best.symbol) : '—'}</strong><small className="positive">{best ? `+${best.change_percent.toFixed(2)}%` : 'No data'}</small></article>
          </div>
          <div className="metric-row previous-row">
            <article><span>Previous close · Portfolio value</span><strong>{money(previousValue)}</strong><small>Prior trading session</small></article>
            <article><span>Previous close · Return</span><strong className={previousPnl >= 0 ? 'positive' : 'negative'}>{previousPnl >= 0 ? '+' : ''}{money(previousPnl)}</strong><small>Previous trading day</small></article>
            <article><span>Previous close · Advancing</span><strong>{previousAdvancing} <i>of {watchlist.length}</i></strong><small>Watchlist breadth</small></article>
            <article><span>Previous close · Best</span><strong>{previousBest ? cleanSymbol(previousBest.stock.symbol) : '—'}</strong><small className="positive">{previousBest ? `${previousBest.change >= 0 ? '+' : ''}${previousBest.change.toFixed(2)}%` : 'No data'}</small></article>
          </div>
        </section>

        <section className="portfolio-layout" id="portfolio">
          <div className="positions">
            <div className="section-title"><span>Your portfolio</span><h2>Positions at the close</h2><p>{myStocks?.last_updated ? `Market data collected ${new Date(myStocks.last_updated).toLocaleString('en-AU')}` : 'Latest available prices'}</p></div>
            <div className="table-head"><span>Company</span><span>Recent trend</span><span>Holding</span><span>Last price</span><span>Today</span></div>
            {positions.map((stock) => {
              const shares = holdings[stock.symbol] || 0;
              const open = openPosition === stock.symbol;
              const stockHistory = myHistory?.stocks.find((item) => item.symbol === stock.symbol);
              return <div className={`position ${open ? 'open' : ''}`} key={stock.symbol}>
                <button className="position-row" onClick={() => setOpenPosition(open ? null : stock.symbol)} aria-expanded={open}>
                  <span className="company"><i>{cleanSymbol(stock.symbol)}</i><span><strong>{cleanSymbol(stock.symbol)}</strong><small>{stock.name}</small></span></span>
                  <Trend history={stockHistory} change={stock.change_percent} />
                  <span className="holding"><strong>{shares ? shares.toLocaleString() : '—'}</strong><small>{shares ? `${money(shares * stock.price)} value` : 'No shares'}</small></span>
                  <span className="price">{money(stock.price)}</span><span className={stock.change_percent >= 0 ? 'positive' : 'negative'}>{stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%</span><b className="chevron">⌄</b>
                </button>
                {open && <div className="position-drawer"><label>Shares held<input type="number" min="0" value={shares || ''} placeholder="0" onChange={(event) => updateHolding(stock.symbol, Number(event.target.value))} /></label><label>Average purchase price<div><span>$</span><input type="number" min="0" step="0.01" value={purchasePrices[stock.symbol] || ''} placeholder="0.00" onChange={(event) => updatePrice(stock.symbol, Number(event.target.value))} /></div></label><p><span>Position value</span><strong>{money(shares * stock.price)}</strong></p><p><span>Today</span><strong className={stock.change >= 0 ? 'positive' : 'negative'}>{stock.change >= 0 ? '+' : ''}{money(shares * stock.change)}</strong></p></div>}
              </div>;
            })}
          </div>

          <aside className="journal" id="archive"><div className="section-title"><span>Market journal</span><h2>Recent sessions</h2></div><div className="journal-list">{sessions.slice(0, 5).map((session, index) => <button className={index === selectedIndex ? 'active' : ''} key={session.filename} onClick={() => fetchArticle(session, index)}><i /><time>{formatDate(session.date, true)}</time><strong>{sessionMood(session)}</strong><p>{compactTitle(session.title)}</p><small>{index === 0 ? 'Latest close' : 'Open session'} →</small></button>)}</div></aside>
        </section>

        <section className="watchlist" id="watchlist">
          <div className="watchlist-title"><div className="section-title"><span>Market watch</span><h2>The names you follow</h2></div><div>{best && <span>Strongest <b className="positive">{cleanSymbol(best.symbol)} +{best.change_percent.toFixed(2)}%</b></span>}{weakest && <span>Weakest <b className="negative">{cleanSymbol(weakest.symbol)} {weakest.change_percent.toFixed(2)}%</b></span>}</div></div>
          <div className="watch-head"><span>Company</span><span>Recent trend</span><span>Last price</span><span>Today</span></div>
          {watchlist.map((stock: Stock) => <a className="watch-row" href={stock.source_url} target="_blank" rel="noreferrer" key={stock.symbol}><span className="company"><i>{cleanSymbol(stock.symbol)}</i><span><strong>{cleanSymbol(stock.symbol)}</strong><small>{stock.name}</small></span></span><Trend history={history?.stocks.find((item) => item.symbol === stock.symbol)} change={stock.change_percent} /><span className="price">{money(stock.price)}</span><span className={stock.change_percent >= 0 ? 'positive' : 'negative'}>{stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%</span></a>)}
        </section>
      </main>
      <footer><a className="wordmark" href="#top">The <em>Closing</em> Ledger</a><p>Personal market intelligence for the Australian close.</p></footer>
      {articleLoading && <div className="loading-toast"><span className="loader" /> Opening session…</div>}
    </div>
  );
}

export default App;
