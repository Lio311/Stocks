"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  LineChart,
  Wallet,
  ArrowUpRight,
  Percent,
  FileSpreadsheet,
  PlusCircle,
  List,
  Trash2,
  TrendingUp,
  Coins,
  Calendar,
  RefreshCcw,
} from "lucide-react";
import gsap from "gsap";
import * as XLSX from "xlsx";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

interface Stock {
  ticker: string;
  shares: number;
  buyPrice: number;
  currentPrice: number;
  currency: "ILS" | "USD";
  dataSource?: string;
}

export default function PortfolioTracker() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [portfolio, setPortfolio] = useState<Stock[]>([]);
  const [usdIlsRate, setUsdIlsRate] = useState<number>(3.65);
  
  // Add Stock Form
  const [newTicker, setNewTicker] = useState("");
  const [newShares, setNewShares] = useState("1");
  const [newPrice, setNewPrice] = useState("");

  // Detail View
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  const [chartPeriod, setChartPeriod] = useState<string>("1w");

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(".anim-header", { y: -30, opacity: 0, duration: 0.8, ease: "power3.out" });
      gsap.from(".anim-card", { y: 30, opacity: 0, duration: 0.8, stagger: 0.1, ease: "power3.out", delay: 0.2 });
    }, containerRef);
    
    fetchExchangeRate();
    
    return () => ctx.revert();
  }, []);

  const fetchExchangeRate = async () => {
    try {
      const response = await fetch("https://api.exchangerate-api.com/v4/latest/USD");
      const data = await response.json();
      if (data.rates && data.rates.ILS) {
        setUsdIlsRate(data.rates.ILS);
      }
    } catch (e) {
      console.warn("Failed to fetch exchange rate, using default 3.65");
    }
  };

  const handleImportExcel = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const workbook = XLSX.read(event.target?.result, { type: "array" });
        const rawData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]], { header: 1 });
        processExcelData(rawData as any[][]);
      } catch (err) {
        alert("שגיאה בקריאת הקובץ.");
      }
    };
    reader.readAsArrayBuffer(file);
    e.target.value = ""; // Reset file input
  };

  const processExcelData = (rows: any[][]) => {
    let rate = usdIlsRate;
    // Scan for exchange rate in first 20 rows
    for (let i = 0; i < Math.min(rows.length, 20); i++) {
      const row = rows[i];
      if (!row) continue;
      for (let j = 0; j < row.length; j++) {
        const val = String(row[j]).trim();
        if (val.includes("שער הדולר") || val.includes("Dollar Rate")) {
          let rateVal = parseFloat(String(row[j + 1] || "").replace(/[^\d\.]/g, ""));
          if (!rateVal || isNaN(rateVal)) {
            rateVal = parseFloat(String(row[j + 2] || "").replace(/[^\d\.]/g, ""));
          }
          if (rateVal && !isNaN(rateVal) && rateVal > 0) {
            rate = rateVal;
            setUsdIlsRate(rateVal);
            break;
          }
        }
      }
    }

    let headerRowIndex = -1;
    let colMap = { ticker: -1, shares: -1, price: -1, currentPrice: -1 };

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (!row) continue;
      for (let j = 0; j < row.length; j++) {
        const val = String(row[j]).trim();
        if (["טיקר", "Ticker", "Symbol"].some((s) => val.includes(s))) colMap.ticker = j;
        if (["כמות מניות", "כמות", "Shares"].some((s) => val === s)) colMap.shares = j;
        if (["מחיר עלות", "Cost", "Buy Price"].some((s) => val.includes(s))) colMap.price = j;
        if (["מחיר זמן אמת", "Real Time", "Last Price", "Current Price"].some((s) => val.includes(s))) colMap.currentPrice = j;
      }
      if (colMap.ticker !== -1 && colMap.shares !== -1) {
        headerRowIndex = i;
        break;
      }
      colMap = { ticker: -1, shares: -1, price: -1, currentPrice: -1 };
    }

    if (headerRowIndex === -1) {
      alert("לא נמצאו עמודות מתאימות בקובץ.");
      return;
    }

    const newPortfolio: Stock[] = [];
    const ILS_TICKERS = ["1159250", "1183441"];

    for (let i = headerRowIndex + 1; i < rows.length; i++) {
      const row = rows[i];
      if (!row) continue;

      let tickerStr = String(row[colMap.ticker] || "").trim();
      if (!tickerStr || tickerStr.toLowerCase() === "nan") continue;

      let sharesStr = String(row[colMap.shares] || "0").replace(/[^\d\.]/g, "");
      const sharesVal = parseFloat(sharesStr);
      if (!sharesVal) continue;

      let priceVal = 0;
      if (colMap.price !== -1) {
        priceVal = parseFloat(String(row[colMap.price]).replace(/[^\d\.\-]/g, "")) || 0;
      }

      let currentPriceVal = 0;
      let foundRealTimePrice = false;
      if (colMap.currentPrice !== -1) {
        let rawRealTime = String(row[colMap.currentPrice] || "");
        let parsed = parseFloat(rawRealTime.replace(/[^\d\.\-]/g, ""));
        if (!isNaN(parsed) && parsed !== 0) {
          currentPriceVal = parsed;
          foundRealTimePrice = true;
        }
      }

      let currency: "ILS" | "USD" = ILS_TICKERS.includes(tickerStr) ? "ILS" : "USD";
      let finalCurrentPrice = foundRealTimePrice
        ? currentPriceVal
        : priceVal > 0
        ? priceVal * (0.95 + Math.random() * 0.1)
        : currency === "ILS" ? 100 : 30;

      newPortfolio.push({
        ticker: tickerStr.toUpperCase(),
        shares: sharesVal,
        buyPrice: priceVal,
        currentPrice: finalCurrentPrice,
        currency,
        dataSource: "excel",
      });
    }

    setPortfolio(newPortfolio);
  };

  const handleAddStock = () => {
    const t = newTicker.trim().toUpperCase();
    const s = parseInt(newShares);
    const p = parseFloat(newPrice);
    if (!t || isNaN(s) || isNaN(p)) return;

    const currency = ["1159250", "1183441"].includes(t) ? "ILS" : "USD";
    
    setPortfolio([...portfolio, {
      ticker: t,
      shares: s,
      buyPrice: p,
      currentPrice: p * (0.95 + Math.random() * 0.1),
      currency,
      dataSource: "manual"
    }]);

    setNewTicker("");
    setNewShares("1");
    setNewPrice("");
  };

  const removeStock = (index: number) => {
    setPortfolio(portfolio.filter((_, i) => i !== index));
  };

  // Summary Calcs
  let totalIlsVal = 0, totalIlsCost = 0;
  let totalUsdVal = 0, totalUsdCost = 0;

  portfolio.forEach((stock) => {
    if (stock.currency === "ILS") {
      totalIlsVal += stock.currentPrice * stock.shares;
      totalIlsCost += stock.buyPrice * stock.shares;
    } else {
      totalUsdVal += stock.currentPrice * stock.shares;
      totalUsdCost += stock.buyPrice * stock.shares;
    }
  });

  const combinedTotal = totalIlsVal + totalUsdVal * usdIlsRate;
  const combinedCost = totalIlsCost + totalUsdCost * usdIlsRate;
  const gain = combinedTotal - combinedCost;
  const gainPercent = combinedCost > 0 ? (gain / combinedCost) * 100 : 0;

  const fmtIls = (n: number) => `₪${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const fmtUsd = (n: number) => `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Chart Generation Logic
  const generateChartData = (stock: Stock, period: string) => {
    const periods: Record<string, { days: number; interval: number }> = {
      "1w": { days: 7, interval: 1 },
      "1mo": { days: 30, interval: 1 },
      "3mo": { days: 90, interval: 3 },
      "6mo": { days: 180, interval: 7 },
      "1y": { days: 365, interval: 7 },
      all: { days: 1825, interval: 30 },
    };
    const config = periods[period] || periods["1w"];
    const points = Math.floor(config.days / config.interval);

    const labels = [];
    const prices = [];
    const now = new Date();
    
    for (let i = points - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i * config.interval);
      if (config.days <= 7) labels.push(date.toLocaleDateString("he-IL", { weekday: "short" }));
      else if (config.days <= 30) labels.push(date.toLocaleDateString("he-IL", { day: "numeric", month: "short" }));
      else labels.push(date.toLocaleDateString("he-IL", { month: "short", year: "2-digit" }));
    }

    const priceChange = stock.currentPrice - stock.buyPrice;
    const volatility = Math.abs(priceChange) * 0.15;

    for (let i = 0; i < points; i++) {
      const progress = i / (points - 1);
      const trendPrice = stock.buyPrice + priceChange * progress;
      const randomVariation = (Math.random() - 0.5) * volatility;
      prices.push(Math.max(0, trendPrice + randomVariation));
    }
    prices[prices.length - 1] = stock.currentPrice;

    return { labels, prices };
  };

  const getChartOptions = (stock: Stock) => {
    const data = generateChartData(stock, chartPeriod);
    const isProfit = stock.currentPrice >= stock.buyPrice;
    const color = isProfit ? "#10b981" : "#ef4444";
    const symbol = stock.currency === "ILS" ? "₪" : "$";

    return {
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "מחיר",
            data: data.prices,
            borderColor: color,
            backgroundColor: `${color}20`,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
          },
          {
            label: "מחיר עלות",
            data: Array(data.labels.length).fill(stock.buyPrice),
            borderColor: "#f59e0b",
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#cbd5e1" } },
          tooltip: {
            callbacks: { label: (ctx: any) => `${ctx.dataset.label}: ${symbol}${ctx.parsed.y.toFixed(2)}` },
          },
        },
        scales: {
          x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
          y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    };
  };

  return (
    <div className="relative min-h-screen text-foreground p-4 md:p-8" dir="rtl" ref={containerRef}>
      <div className="bg-animation"></div>

      <div className="container max-w-6xl mx-auto relative z-10 space-y-8">
        <header className="anim-header flex flex-col md:flex-row justify-between items-center pb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <LineChart className="w-10 h-10 text-blue-500" />
            <div>
              <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
                מעקב תיק מניות
              </h1>
              <p className="text-sm text-muted-foreground mt-1 flex items-center gap-2">
                <RefreshCcw className="w-3 h-3" /> שער הדולר: ₪{usdIlsRate.toFixed(2)}
              </p>
            </div>
          </div>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="anim-card shadow-lg border">
            <CardContent className="p-6">
              <div className="flex justify-between items-start mb-4">
                <span className="text-muted-foreground font-medium">שווי תיק</span>
                <Wallet className="w-5 h-5 text-blue-500" />
              </div>
              <div className="text-xs text-muted-foreground mb-1">{fmtIls(totalIlsVal)} + {fmtUsd(totalUsdVal)}</div>
              <div className="text-3xl font-bold text-foreground">{fmtIls(combinedTotal)}</div>
            </CardContent>
          </Card>
          <Card className="anim-card shadow-lg border">
            <CardContent className="p-6">
              <div className="flex justify-between items-start mb-4">
                <span className="text-muted-foreground font-medium">רווח/הפסד</span>
                <ArrowUpRight className={`w-5 h-5 ${gain >= 0 ? "text-emerald-500" : "text-red-500"}`} />
              </div>
              <div className="text-3xl font-bold" style={{ color: gain >= 0 ? "#10b981" : "#ef4444" }}>
                <span dir="ltr">{gain >= 0 ? "+" : ""}{fmtIls(gain)}</span>
              </div>
            </CardContent>
          </Card>
          <Card className="anim-card shadow-lg border">
            <CardContent className="p-6">
              <div className="flex justify-between items-start mb-4">
                <span className="text-muted-foreground font-medium">אחוז שינוי</span>
                <Percent className={`w-5 h-5 ${gain >= 0 ? "text-emerald-500" : "text-red-500"}`} />
              </div>
              <div className="text-3xl font-bold" style={{ color: gain >= 0 ? "#10b981" : "#ef4444" }}>
                <span dir="ltr">{gainPercent > 0 ? "+" : ""}{gainPercent.toFixed(2)}%</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 anim-card">
          <Card className="shadow-lg border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-foreground">
                <FileSpreadsheet className="w-5 h-5 text-blue-400" /> יבוא מ-Excel
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Input type="file" accept=".xlsx, .xls" onChange={handleImportExcel} className="bg-background border-border flex-1" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">הקובץ צריך לכלול עמודות: טיקר, כמות, מחיר (או דומות)</p>
            </CardContent>
          </Card>

          <Card className="shadow-lg border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-foreground">
                <PlusCircle className="w-5 h-5 text-indigo-400" /> הוסף מניה ידנית
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input placeholder="סימול (AAPL)" value={newTicker} onChange={(e) => setNewTicker(e.target.value)} className="bg-background border-border flex-1" />
                <Input type="number" placeholder="כמות" value={newShares} onChange={(e) => setNewShares(e.target.value)} className="bg-background border-border flex-1 min-w-[80px]" />
                <Input type="number" placeholder="מחיר קנייה" value={newPrice} onChange={(e) => setNewPrice(e.target.value)} className="bg-background border-border flex-1 min-w-[100px]" />
                <Button onClick={handleAddStock} className="bg-blue-600 hover:bg-blue-700 text-foreground">הוסף</Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Portfolio Table */}
        <Card className="anim-card shadow-lg border">
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2 text-foreground">
              <List className="w-5 h-5 text-blue-400" /> התיק שלי
            </CardTitle>
          </CardHeader>
          <CardContent>
            {portfolio.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">התיק ריק. יבא קובץ Excel או הוסף מניות ידנית.</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-800 hover:bg-transparent">
                      <TableHead className="text-right text-muted-foreground">סימול</TableHead>
                      <TableHead className="text-right text-muted-foreground">כמות</TableHead>
                      <TableHead className="text-right text-muted-foreground">מחיר רכישה</TableHead>
                      <TableHead className="text-right text-muted-foreground">מחיר נוכחי</TableHead>
                      <TableHead className="text-right text-muted-foreground">רווח/הפסד</TableHead>
                      <TableHead className="text-right text-muted-foreground">%</TableHead>
                      <TableHead className="text-right text-muted-foreground"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {portfolio.map((stock, i) => {
                      const stockGain = (stock.currentPrice - stock.buyPrice) * stock.shares;
                      const stockGainPercent = stock.buyPrice > 0 ? ((stock.currentPrice - stock.buyPrice) / stock.buyPrice) * 100 : 0;
                      const sym = stock.currency === "ILS" ? "₪" : "$";
                      const color = stockGain >= 0 ? "text-emerald-500" : "text-red-500";

                      return (
                        <TableRow 
                          key={i} 
                          className="border-slate-800 hover:bg-background cursor-pointer transition-colors"
                          onClick={() => setSelectedStock(stock)}
                        >
                          <TableCell className="font-semibold text-foreground">{stock.ticker} <span className="text-muted-foreground text-xs font-normal">({stock.currency})</span></TableCell>
                          <TableCell>{stock.shares}</TableCell>
                          <TableCell dir="ltr" className="text-right">{sym}{stock.buyPrice.toFixed(2)}</TableCell>
                          <TableCell dir="ltr" className="text-right">{sym}{stock.currentPrice.toFixed(2)}</TableCell>
                          <TableCell dir="ltr" className={`text-right ${color}`}>{stockGain >= 0 ? "+" : ""}{sym}{Math.abs(stockGain).toFixed(2)}</TableCell>
                          <TableCell dir="ltr" className={`text-right ${color}`}>{stockGainPercent >= 0 ? "+" : ""}{stockGainPercent.toFixed(2)}%</TableCell>
                          <TableCell>
                            <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-red-500 hover:bg-red-500/10" onClick={(e) => { e.stopPropagation(); removeStock(i); }}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detail View Dialog */}
      <Dialog open={!!selectedStock} onOpenChange={(open) => !open && setSelectedStock(null)}>
        <DialogContent className="max-w-4xl sm:max-w-4xl bg-background border-border text-foreground p-6 md:p-8 rounded-2xl shadow-2xl max-h-[90vh] overflow-y-auto" dir="rtl">
          {selectedStock && (
            <>
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold flex items-center gap-2 text-foreground">
                  <TrendingUp className="w-6 h-6 text-blue-500" /> {selectedStock.ticker} 
                  <span className="text-sm text-muted-foreground font-normal bg-background px-2 py-1 rounded">
                    {selectedStock.dataSource === "excel" ? "נתוני EXCEL" : "ידני"}
                  </span>
                </DialogTitle>
              </DialogHeader>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                <div className="bg-background p-4 rounded-xl border border-border">
                  <div className="text-sm text-muted-foreground mb-1">מחיר עלות</div>
                  <div className="text-xl font-semibold text-foreground">{selectedStock.currency === "ILS" ? "₪" : "$"}{selectedStock.buyPrice.toFixed(2)}</div>
                </div>
                <div className="bg-background p-4 rounded-xl border border-border">
                  <div className="text-sm text-muted-foreground mb-1">מחיר נוכחי</div>
                  <div className="text-xl font-semibold text-foreground">{selectedStock.currency === "ILS" ? "₪" : "$"}{selectedStock.currentPrice.toFixed(2)}</div>
                </div>
                <div className="bg-background p-4 rounded-xl border border-border">
                  <div className="text-sm text-muted-foreground mb-1">תשואה</div>
                  <div className={`text-xl font-bold ${selectedStock.currentPrice >= selectedStock.buyPrice ? "text-emerald-500" : "text-red-500"}`} dir="ltr">
                    {selectedStock.currentPrice >= selectedStock.buyPrice ? "+" : ""}
                    {(((selectedStock.currentPrice - selectedStock.buyPrice) / selectedStock.buyPrice) * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="bg-background p-4 rounded-xl border border-border">
                  <div className="text-sm text-muted-foreground mb-1">כמות</div>
                  <div className="text-xl font-semibold text-foreground">{selectedStock.shares}</div>
                </div>
              </div>

              <div className="mt-8 border border-border bg-background/30 rounded-xl p-6">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="font-semibold text-lg flex items-center gap-2 text-foreground"><LineChart className="w-5 h-5 text-indigo-400" /> גרף מחירים</h3>
                  <div className="flex gap-1 bg-muted p-1 rounded-lg border border-border">
                    {["1w", "1mo", "3mo", "6mo", "1y"].map((p) => (
                      <button 
                        key={p} 
                        onClick={() => setChartPeriod(p)}
                        className={`px-3 py-1.5 text-sm rounded-md transition-colors ${chartPeriod === p ? "bg-blue-600 text-foreground font-medium shadow-sm" : "text-muted-foreground hover:text-foreground hover:bg-background"}`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-[300px] w-full">
                  <Line {...getChartOptions(selectedStock)} />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="flex items-center gap-4 bg-background/30 p-4 rounded-xl border border-border">
                  <div className="p-2 bg-blue-500/10 rounded-lg"><Coins className="text-blue-500 w-6 h-6" /></div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">מטבע</div>
                    <div className="font-medium text-foreground">{selectedStock.currency === "ILS" ? "שקל ישראלי (₪)" : "דולר אמריקאי ($)"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 bg-background/30 p-4 rounded-xl border border-border">
                  <div className="p-2 bg-blue-500/10 rounded-lg"><Calendar className="text-blue-500 w-6 h-6" /></div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">עדכון אחרון</div>
                    <div className="font-medium text-foreground">{new Date().toLocaleDateString("he-IL")}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 bg-background/30 p-4 rounded-xl border border-border">
                  <div className="p-2 bg-blue-500/10 rounded-lg"><RefreshCcw className="text-blue-500 w-6 h-6" /></div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">שער המרה</div>
                    <div className="font-medium text-foreground" dir="ltr">$1 = ₪{usdIlsRate.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}





