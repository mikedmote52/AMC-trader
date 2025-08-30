import React, { useState, useEffect, useRef } from "react";
import { API_BASE } from "../config";
import "./SqueezeAlert.css"; // Reuse flash animations

interface PnLUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  market_value: number;
}

interface RealTimePnLProps {
  symbol: string;
  initialPrice?: number;
  initialPnL?: number;
  position?: any;
  onSignificantMove?: (symbol: string, changePercent: number) => void;
}

export default function RealTimePnL({ 
  symbol, 
  initialPrice = 0, 
  initialPnL = 0, 
  position,
  onSignificantMove 
}: RealTimePnLProps) {
  const [currentPrice, setCurrentPrice] = useState(initialPrice);
  const [currentPnL, setCurrentPnL] = useState(initialPnL);
  const [priceChange, setPriceChange] = useState(0);
  const [changePercent, setChangePercent] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [flashClass, setFlashClass] = useState("");
  
  const wsRef = useRef<WebSocket | null>(null);
  const previousPriceRef = useRef(initialPrice);
  const audioContextRef = useRef<AudioContext | null>(null);
  
  // Initialize audio context for alerts
  useEffect(() => {
    // Create audio context on user interaction to avoid browser restrictions
    const initAudioContext = () => {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
    };
    
    document.addEventListener('click', initAudioContext, { once: true });
    document.addEventListener('touchstart', initAudioContext, { once: true });
    
    return () => {
      document.removeEventListener('click', initAudioContext);
      document.removeEventListener('touchstart', initAudioContext);
    };
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      try {
        // Convert HTTP API base to WebSocket URL
        const wsUrl = API_BASE.replace(/^https?:/, 'wss:').replace(/^http:/, 'ws:') + '/ws/prices';
        
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
          console.log(`WebSocket connected for ${symbol}`);
          setIsConnected(true);
          
          // Subscribe to price updates for this symbol
          wsRef.current?.send(JSON.stringify({
            action: 'subscribe',
            symbol: symbol,
            type: 'price_updates'
          }));
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data: PnLUpdate = JSON.parse(event.data);
            
            // Only process updates for our symbol
            if (data.symbol === symbol) {
              const newPrice = data.price;
              const oldPrice = previousPriceRef.current;
              
              // Calculate change
              const change = newPrice - oldPrice;
              const changePercent = oldPrice > 0 ? (change / oldPrice) * 100 : 0;
              
              // Update state
              setCurrentPrice(newPrice);
              setCurrentPnL(data.unrealized_pl || calculatePnL(newPrice));
              setPriceChange(change);
              setChangePercent(changePercent);
              setLastUpdate(new Date());
              
              // Flash animation based on price movement
              if (Math.abs(change) > 0.01) { // Only flash for meaningful changes
                const flashType = change > 0 ? 'price-flash-green' : 'price-flash-red';
                setFlashClass(flashType);
                setTimeout(() => setFlashClass(''), 600);
              }
              
              // Audio alert for significant moves (>5%)
              if (Math.abs(changePercent) > 5) {
                playAudioAlert(changePercent > 0);
                onSignificantMove?.(symbol, changePercent);
              }
              
              previousPriceRef.current = newPrice;
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        wsRef.current.onerror = (error) => {
          console.error(`WebSocket error for ${symbol}:`, error);
          setIsConnected(false);
        };
        
        wsRef.current.onclose = () => {
          console.log(`WebSocket closed for ${symbol}`);
          setIsConnected(false);
          
          // Attempt to reconnect after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };
        
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        setIsConnected(false);
      }
    };

    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [symbol, onSignificantMove]);

  // Fallback to polling if WebSocket fails
  useEffect(() => {
    if (!isConnected) {
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/market/quote/${symbol}`);
          if (response.ok) {
            const data = await response.json();
            if (data.price) {
              const newPrice = data.price;
              const oldPrice = previousPriceRef.current;
              const change = newPrice - oldPrice;
              const changePercent = oldPrice > 0 ? (change / oldPrice) * 100 : 0;
              
              setCurrentPrice(newPrice);
              setCurrentPnL(data.unrealized_pl || calculatePnL(newPrice));
              setPriceChange(change);
              setChangePercent(changePercent);
              setLastUpdate(new Date());
              
              previousPriceRef.current = newPrice;
            }
          }
        } catch (error) {
          console.error('Polling error:', error);
        }
      }, 5000); // Poll every 5 seconds as fallback
      
      return () => clearInterval(pollInterval);
    }
  }, [isConnected, symbol]);

  const calculatePnL = (price: number) => {
    if (!position) return 0;
    return (price - position.avg_entry_price) * position.qty;
  };

  const playAudioAlert = (isPositive: boolean) => {
    if (!audioContextRef.current) return;
    
    try {
      const oscillator = audioContextRef.current.createOscillator();
      const gainNode = audioContextRef.current.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContextRef.current.destination);
      
      // Different tones for positive/negative moves
      oscillator.frequency.value = isPositive ? 800 : 400;
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.1, audioContextRef.current.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContextRef.current.currentTime + 0.5);
      
      oscillator.start();
      oscillator.stop(audioContextRef.current.currentTime + 0.5);
    } catch (error) {
      console.error('Audio alert error:', error);
    }
  };

  const formatTime = (date: Date | null) => {
    if (!date) return "Never";
    return date.toLocaleTimeString();
  };

  const getChangeColor = () => {
    if (changePercent > 0) return "#22c55e";
    if (changePercent < 0) return "#ef4444";
    return "#6b7280";
  };

  const getChangeIcon = () => {
    if (changePercent > 0) return "📈";
    if (changePercent < 0) return "📉";
    return "➡️";
  };

  return (
    <div style={containerStyle} className={flashClass}>
      {/* Connection Status */}
      <div style={statusStyle}>
        <span style={{
          color: isConnected ? "#22c55e" : "#f59e0b",
          fontSize: "12px",
          fontWeight: 600
        }}>
          {isConnected ? "🟢 LIVE" : "🟡 POLLING"}
        </span>
        <span style={timestampStyle}>
          {formatTime(lastUpdate)}
        </span>
      </div>

      {/* Price Display */}
      <div style={priceDisplayStyle}>
        <div style={symbolStyle}>{symbol}</div>
        <div style={currentPriceStyle}>
          ${currentPrice.toFixed(2)}
        </div>
      </div>

      {/* Change Indicators */}
      <div style={changeStyle}>
        <span style={{ color: getChangeColor(), fontSize: "16px" }}>
          {getChangeIcon()}
        </span>
        <span style={{ color: getChangeColor(), fontWeight: 700 }}>
          ${priceChange.toFixed(2)} ({changePercent >= 0 ? "+" : ""}{changePercent.toFixed(2)}%)
        </span>
      </div>

      {/* P&L Display */}
      {position && (
        <div style={pnlStyle}>
          <span style={pnlLabelStyle}>Unrealized P&L:</span>
          <span style={{
            ...pnlValueStyle,
            color: currentPnL >= 0 ? "#22c55e" : "#ef4444"
          }}>
            ${currentPnL.toFixed(2)}
          </span>
        </div>
      )}

      {/* Significant Move Alert */}
      {Math.abs(changePercent) > 5 && (
        <div style={alertBadgeStyle}>
          🚨 {Math.abs(changePercent).toFixed(1)}% MOVE
        </div>
      )}
    </div>
  );
}

// Styles
const containerStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  minWidth: "200px",
  transition: "all 0.3s ease"
};

const statusStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: "11px"
};

const timestampStyle: React.CSSProperties = {
  color: "#666",
  fontSize: "11px"
};

const priceDisplayStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const symbolStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#fff"
};

const currentPriceStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 800,
  color: "#fff"
};

const changeStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  fontSize: "14px"
};

const pnlStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "8px 0",
  borderTop: "1px solid #333"
};

const pnlLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999"
};

const pnlValueStyle: React.CSSProperties = {
  fontSize: "14px",
  fontWeight: 700
};

const alertBadgeStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #ef4444, #dc2626)",
  color: "#fff",
  padding: "6px 12px",
  borderRadius: "20px",
  fontSize: "11px",
  fontWeight: 700,
  textAlign: "center",
  textTransform: "uppercase",
  animation: "pulse 1s infinite"
};