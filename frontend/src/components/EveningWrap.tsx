import { useMemo } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import type { EveningWrap as EveningWrapType, EveningWrapListItem, DailyPnLResponse } from '../types';

interface EveningWrapProps {
  article: EveningWrapType | null;
  articleList: EveningWrapListItem[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  loading?: boolean;
  dailyPnL?: DailyPnLResponse | null;
}

export function EveningWrap({
  article,
  articleList,
  selectedDate,
  onSelectDate,
  loading,
  dailyPnL,
}: EveningWrapProps) {
  // Convert YYYYMMDD string to Date object
  const parseDate = (dateString: string): Date => {
    const normalized = dateString.includes('-')
      ? dateString
      : `${dateString.slice(0, 4)}-${dateString.slice(4, 6)}-${dateString.slice(6, 8)}`;
    return new Date(normalized);
  };

  // Convert Date to YYYYMMDD string
  const formatDateToString = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  };

  // Get stored P&L records (calculated at scrape time)
  const storedPnL = useMemo(() => {
    if (!dailyPnL?.records) return {};

    // Convert to simple date -> pnl mapping
    const pnlByDate: Record<string, number> = {};
    Object.entries(dailyPnL.records).forEach(([date, record]) => {
      pnlByDate[date] = record.pnl;
    });

    return pnlByDate;
  }, [dailyPnL]);

  // Convert Date to YYYY-MM-DD string for lookup
  const formatDateToISO = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Get P&L for a specific date
  const getPnLForDate = (date: Date): number | null => {
    const dateStr = formatDateToISO(date);
    return storedPnL[dateStr] ?? null;
  };

  // Get available dates as Date objects
  const availableDates = useMemo(() => {
    return articleList.map((item) => {
      const dateStr = item.filename.replace('evening_wrap_', '').replace('.json', '');
      return parseDate(dateStr);
    });
  }, [articleList]);

  // Get selected date as Date object
  const selectedDateObj = useMemo(() => {
    if (!selectedDate) return null;
    return parseDate(selectedDate);
  }, [selectedDate]);

  // Handle date selection from calendar
  const handleDateChange = (date: Date | null) => {
    if (date) {
      onSelectDate(formatDateToString(date));
    }
  };

  // Check if a date has an article
  const isDateAvailable = (date: Date): boolean => {
    return availableDates.some(
      (d) => d.toDateString() === date.toDateString()
    );
  };

  // Check if a date is selected
  const isSelected = (date: Date): boolean => {
    if (!selectedDateObj) return false;
    return date.toDateString() === selectedDateObj.toDateString();
  };

  // Render custom day contents with P&L for each trading day
  const renderDayContents = (day: number, date: Date | undefined) => {
    if (!date) return <span>{day}</span>;

    const pnl = getPnLForDate(date);
    const showPnL = pnl !== null && pnl !== 0;
    const selected = isSelected(date);

    // Use white/light colors when selected (dark background), normal colors otherwise
    const pnlColorClass = selected
      ? (pnl && pnl >= 0 ? 'text-green-300' : 'text-red-300')
      : (pnl && pnl >= 0 ? 'text-green-600' : 'text-red-600');

    return (
      <div className="flex flex-col items-center leading-none">
        <span>{day}</span>
        {showPnL && (
          <span className={`text-[9px] font-bold ${pnlColorClass}`}>
            {pnl >= 0 ? '+' : ''}{pnl.toFixed(0)}
          </span>
        )}
      </div>
    );
  };

  const formatDateLong = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-AU', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden flex flex-col h-full flex-1 min-h-0">
      <div className="bg-gray-800 text-white px-4 py-3">
        <h2 className="text-lg font-semibold">Evening Wrap</h2>
        {article && (
          <p className="text-sm text-gray-300">{formatDateLong(article.date)}</p>
        )}
      </div>

      {/* Date Selector and Summary */}
      {articleList.length > 0 && (
        <div className="px-4 py-3 border-b bg-gray-50">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Calendar */}
            <div className="flex-shrink-0">
              <DatePicker
                selected={selectedDateObj}
                onChange={handleDateChange}
                includeDates={availableDates}
                filterDate={isDateAvailable}
                inline
                calendarClassName="!border-0 !bg-transparent"
                renderDayContents={renderDayContents}
              />
            </div>

            {/* AI Summary */}
            {article?.summary && (
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <span className="inline-block w-4 h-4">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                  </span>
                  AI Summary
                </h4>
                <div className="text-sm text-gray-600 space-y-1">
                  {article.summary.split('\n').map((line, idx) => {
                    const trimmed = line.trim();
                    if (!trimmed) return null;

                    // Check if line is a section header (starts with emoji)
                    const isSectionHeader = /^[🎯📈📉]/.test(trimmed);

                    // Check if line is a bullet point
                    const isBullet = trimmed.startsWith('*') || trimmed.startsWith('•') || trimmed.startsWith('-');
                    const bulletContent = isBullet ? trimmed.replace(/^[*•\-]\s*/, '') : trimmed;

                    if (isSectionHeader) {
                      return (
                        <p key={idx} className="leading-relaxed font-semibold text-gray-800 mt-3 mb-1">
                          {trimmed}
                        </p>
                      );
                    }

                    if (isBullet) {
                      return (
                        <p key={idx} className="leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-gray-400">
                          {bulletContent}
                        </p>
                      );
                    }

                    return (
                      <p key={idx} className="leading-relaxed">
                        {trimmed}
                      </p>
                    );
                  })}
                </div>
              </div>
            )}

            {/* No Summary State */}
            {article && !article.summary && (
              <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
                No AI summary available
              </div>
            )}
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800 mx-auto"></div>
            <p className="mt-2 text-gray-500">Loading article...</p>
          </div>
        </div>
      )}

      {/* No Article State */}
      {!loading && !article && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center text-gray-500">
            {articleList.length > 0
              ? 'Select a date to view the article'
              : 'No evening wrap articles available'}
          </div>
        </div>
      )}

      {/* Article Content */}
      {!loading && article && (
        <>
          <div className="p-4 border-b">
            <h3 className="text-xl font-bold text-gray-900 mb-2">{article.title}</h3>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              View original article
            </a>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {/* Use formatted HTML content if available */}
            {article.formatted_content ? (
              <div
                className="prose prose-sm max-w-none
                  [&_table]:w-full [&_table]:text-sm [&_table]:border-collapse [&_table]:my-4
                  [&_th]:bg-gray-100 [&_th]:font-semibold [&_th]:px-3 [&_th]:py-2 [&_th]:border [&_th]:border-gray-200 [&_th]:text-left
                  [&_td]:px-3 [&_td]:py-1.5 [&_td]:border [&_td]:border-gray-200
                  [&_tr:nth-child(even)]:bg-gray-50
                  [&_h2]:font-bold [&_h2]:text-gray-900 [&_h2]:mt-8 [&_h2]:mb-4 [&_h2]:text-xl [&_h2]:border-b-2 [&_h2]:border-gray-300 [&_h2]:pb-2
                  [&_h3]:font-semibold [&_h3]:text-gray-800 [&_h3]:mt-5 [&_h3]:mb-3 [&_h3]:text-lg
                  [&_h4]:font-medium [&_h4]:text-gray-700 [&_h4]:mt-4 [&_h4]:mb-2 [&_h4]:text-base
                  [&_p]:text-gray-700 [&_p]:mb-2"
                dangerouslySetInnerHTML={{ __html: article.formatted_content }}
              />
            ) : (
              <div className="prose prose-sm max-w-none">
                {/* Fallback: parse raw content */}
                {article.content.split('\n').map((line, idx) => {
                  if (!line.trim()) return null;
                  const isHeader = line.length < 100 && (line === line.toUpperCase() || line.endsWith(':'));
                  if (isHeader) {
                    return <h4 key={idx} className="font-bold text-gray-800 mt-4 mb-2">{line}</h4>;
                  }
                  return <p key={idx} className="text-gray-700 mb-2">{line}</p>;
                })}
              </div>
            )}
          </div>

          <div className="px-4 py-2 bg-gray-50 text-xs text-gray-500 border-t">
            Scraped: {new Date(article.scraped_at).toLocaleString('en-AU')}
          </div>
        </>
      )}
    </div>
  );
}
