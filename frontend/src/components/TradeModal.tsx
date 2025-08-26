import { useState, useEffect } from "react";
import { API_BASE } from '../config';

interface TradeModalProps {
  candidate?: any;
  symbol?: string;
  action?: 'BUY' | 'SELL';
  qty?: number;
  onClose: () => void;
}

export default function TradeModal({ candidate, symbol, action = 'BUY', qty, onClose }: TradeModalProps) {
  const tradeSymbol = candidate?.symbol || symbol || '';
  
  const [amount, setAmount] = useState(100);
  const [shares, setShares] = useState<string>(qty?.toString() || "");
  const [orderType, setOrderType] = useState<"market"|"limit">("market");
  const [limitPrice, setLimitPrice] = useState<string>("");
  const [useBracket, setUseBracket] = useState(false);
  const [usePercent, setUsePercent] = useState(true);
  const [tpPct, setTpPct] = useState<string>("");
  const [slPct, setSlPct] = useState<string>("");
  const [tpAbs, setTpAbs] = useState<string>("");
  const [slAbs, setSlAbs] = useState<string>("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  // Trade defaults from API
  const [lastPrice, setLastPrice] = useState<number>(0);
  const [priceCap, setPriceCap] = useState<number>(100);
  const [defaultTpPct, setDefaultTpPct] = useState<number>(0);
  const [defaultSlPct, setDefaultSlPct] = useState<number>(0);
  const [defaultTpAbs, setDefaultTpAbs] = useState<number>(0);
  const [defaultSlAbs, setDefaultSlAbs] = useState<number>(0);

  // Fetch trade defaults on mount
  useEffect(() => {
    if (!tradeSymbol) return;
    
    const fetchDefaults = async () => {
      try {
        const response = await fetch(`${API_BASE}/trades/defaults/${tradeSymbol}`);
        if (response.ok) {
          const defaults = await response.json();
          setLastPrice(defaults.last_price || 0);
          setPriceCap(defaults.price_cap || 100);
          
          if (defaults.bracket) {
            setUseBracket(true);
            if (defaults.take_profit_pct) {
              setDefaultTpPct(defaults.take_profit_pct);
              setTpPct((defaults.take_profit_pct * 100).toString());
            }
            if (defaults.stop_loss_pct) {
              setDefaultSlPct(defaults.stop_loss_pct);
              setSlPct((defaults.stop_loss_pct * 100).toString());
            }
            if (defaults.take_profit_price) {
              setDefaultTpAbs(defaults.take_profit_price);
              setTpAbs(defaults.take_profit_price.toString());
            }
            if (defaults.stop_loss_price) {
              setDefaultSlAbs(defaults.stop_loss_price);
              setSlAbs(defaults.stop_loss_price.toString());
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch trade defaults:', error);
      }
    };
    
    fetchDefaults();
  }, [tradeSymbol]);

  // Validation logic
  const notionalAmount = Number(amount) || 0;
  const shareCount = Number(shares) || 0;
  const sharesValue = shareCount * lastPrice;
  
  const isNotionalExceeded = notionalAmount > priceCap;
  const isSharesExceeded = sharesValue > priceCap;
  const isDisabled = isNotionalExceeded || isSharesExceeded || loading;

  const validationMessage = isNotionalExceeded 
    ? `Max spend is $${priceCap}`
    : isSharesExceeded 
    ? `Max spend is $${priceCap} (${shareCount} shares × $${lastPrice.toFixed(2)} = $${sharesValue.toFixed(2)})`
    : null;

  async function submit() {
    setLoading(true); 
    setMsg(null);
    
    try {
      const body: any = {
        symbol: tradeSymbol.toUpperCase(),
        action: action,
        mode: "live",
        order_type: orderType,
        time_in_force: "day",
      };
      
      if (shares && Number(shares) > 0) {
        body.qty = Number(shares);
      } else {
        body.notional_usd = Number(amount);
      }
      
      if (orderType === "limit" && limitPrice) {
        body.price = Number(limitPrice);
      }
      
      if (useBracket) {
        body.bracket = true;
        if (usePercent) {
          if (tpPct) body.take_profit_pct = Number(tpPct) / 100.0;
          if (slPct) body.stop_loss_pct = Number(slPct) / 100.0;
        } else {
          if (tpAbs) body.take_profit_price = Number(tpAbs);
          if (slAbs) body.stop_loss_price = Number(slAbs);
        }
      }
      
      const response = await fetch(`${API_BASE}/trades/execute`, {
        method: "POST", 
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      });
      
      const json = await response.json();
      
      if (!response.ok) {
        // Handle price cap exceeded error
        if (json.error === "price_cap_exceeded") {
          setMsg(`Price cap exceeded. Max: $${json.cap || priceCap}, Current price: $${json.price || lastPrice}`);
        } else {
          throw json;
        }
      } else {
        // Success
        const orderId = json?.execution_result?.alpaca_order_id || json?.order_id || json?.id;
        const baseMsg = json?.execution_result?.alpaca_order_id ? "Live order submitted" : "Order accepted";
        setMsg(orderId ? `${baseMsg} (Order ID: ${orderId})` : baseMsg);
        
        // Trigger a holdings refresh
        window.dispatchEvent(new CustomEvent('holdingsRefresh'));
      }
    } catch (e: any) {
      const err = e?.error || e?.detail || e;
      setMsg(typeof err === "string" ? err : JSON.stringify(err));
    } finally { 
      setLoading(false); 
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-slate-800 p-6 rounded-xl max-w-md w-full mx-4 space-y-4">
        <div className="text-lg font-semibold text-white">
          {action} {tradeSymbol.toUpperCase()}
          {lastPrice > 0 && <span className="text-sm font-normal text-gray-300 ml-2">@ ${lastPrice.toFixed(2)}</span>}
        </div>
        
        <div className="space-y-2">
          <label className="block text-sm text-gray-300">Amount</label>
          <div className="flex flex-wrap gap-2 items-center">
            <input 
              className="px-3 py-2 rounded border bg-slate-700 text-white w-32" 
              type="number" 
              min="1"
              value={amount} 
              onChange={(e) => setAmount(Number(e.target.value || 0))} 
              placeholder="$ Notional"
            />
            <span className="text-gray-400">or</span>
            <input 
              className="px-3 py-2 rounded border bg-slate-700 text-white w-24" 
              type="number" 
              min="1"
              value={shares} 
              onChange={(e) => setShares(e.target.value)} 
              placeholder="# shares"
            />
          </div>
          {validationMessage && (
            <div className="text-red-400 text-sm">{validationMessage}</div>
          )}
        </div>
        
        <div className="space-y-2">
          <label className="block text-sm text-gray-300">Order Type</label>
          <div className="flex gap-2 items-center">
            <select 
              className="px-3 py-2 rounded border bg-slate-700 text-white" 
              value={orderType} 
              onChange={(e) => setOrderType(e.target.value as any)}
            >
              <option value="market">Market</option>
              <option value="limit">Limit</option>
            </select>
            {orderType === "limit" && (
              <input 
                className="px-3 py-2 rounded border bg-slate-700 text-white w-28" 
                type="number" 
                min="0" 
                step="0.01"
                value={limitPrice} 
                onChange={(e) => setLimitPrice(e.target.value)} 
                placeholder="Limit price"
              />
            )}
          </div>
        </div>
        
        <label className="flex items-center gap-2 text-white">
          <input 
            type="checkbox" 
            checked={useBracket} 
            onChange={(e) => setUseBracket(e.target.checked)} 
          />
          Add take-profit / stop-loss
        </label>
        
        {useBracket && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <button 
                className={`px-3 py-1 rounded text-sm ${usePercent ? 'bg-blue-600 text-white' : 'bg-slate-600 text-gray-300'}`}
                onClick={() => setUsePercent(true)}
              >
                Percent
              </button>
              <button 
                className={`px-3 py-1 rounded text-sm ${!usePercent ? 'bg-blue-600 text-white' : 'bg-slate-600 text-gray-300'}`}
                onClick={() => setUsePercent(false)}
              >
                Absolute
              </button>
            </div>
            
            {usePercent ? (
              <div className="grid grid-cols-2 gap-2">
                <input 
                  className="px-3 py-2 rounded border bg-slate-700 text-white" 
                  type="number" 
                  min="0" 
                  step="0.1"
                  value={tpPct} 
                  onChange={(e) => setTpPct(e.target.value)} 
                  placeholder="TP % (e.g. 5)"
                />
                <input 
                  className="px-3 py-2 rounded border bg-slate-700 text-white" 
                  type="number" 
                  min="0" 
                  step="0.1"
                  value={slPct} 
                  onChange={(e) => setSlPct(e.target.value)} 
                  placeholder="SL % (e.g. 3)"
                />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <input 
                  className="px-3 py-2 rounded border bg-slate-700 text-white" 
                  type="number" 
                  min="0" 
                  step="0.01"
                  value={tpAbs} 
                  onChange={(e) => setTpAbs(e.target.value)} 
                  placeholder="TP price"
                />
                <input 
                  className="px-3 py-2 rounded border bg-slate-700 text-white" 
                  type="number" 
                  min="0" 
                  step="0.01"
                  value={slAbs} 
                  onChange={(e) => setSlAbs(e.target.value)} 
                  placeholder="SL price"
                />
              </div>
            )}
          </div>
        )}
        
        <div className="flex gap-2 pt-2">
          <button 
            onClick={submit} 
            disabled={isDisabled}
            className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed flex-1"
          >
            {loading ? "Submitting..." : `Submit ${action} order`}
          </button>
          <button 
            onClick={onClose} 
            className="px-4 py-2 rounded border border-gray-500 text-white hover:bg-slate-700"
          >
            Close
          </button>
        </div>
        
        {msg && (
          <div className="text-sm break-all text-gray-300 bg-slate-700 p-2 rounded">
            {msg}
          </div>
        )}
      </div>
    </div>
  );
}