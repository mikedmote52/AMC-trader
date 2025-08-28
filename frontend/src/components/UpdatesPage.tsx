import React, { useEffect, useState } from "react";
import { API_BASE } from "../config";
import { getJSON } from "../lib/api";

type Update = {
  time: string;
  type: string;
  title: string;
  summary: string;
  details: any;
  sms_text: string;
  action_items: string[];
};

export default function UpdatesPage() {
  const [updates, setUpdates] = useState<Update[]>([]);
  const [currentUpdate, setCurrentUpdate] = useState<Update | null>(null);
  const [loading, setLoading] = useState(true);
  const [smsStatus, setSmsStatus] = useState<string>("");

  useEffect(() => {
    const loadUpdates = async () => {
      try {
        const [currentResponse, allResponse] = await Promise.all([
          getJSON(`${API_BASE}/daily-updates/current`),
          getJSON(`${API_BASE}/daily-updates/all`)
        ]);

        if (currentResponse?.success) {
          setCurrentUpdate(currentResponse.data);
        }

        if (allResponse?.success) {
          setUpdates(allResponse.data);
        }
      } catch (error) {
        console.error("Failed to load updates:", error);
      } finally {
        setLoading(false);
      }
    };

    loadUpdates();
    const interval = setInterval(loadUpdates, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const sendSMSUpdate = async (updateType: string = "current") => {
    try {
      setSmsStatus("Sending...");
      const response = await getJSON(`${API_BASE}/daily-updates/send-sms?update_type=${updateType}`);
      
      if (response?.success) {
        setSmsStatus(`✅ SMS sent to ...${response.phone_number}`);
      } else {
        setSmsStatus(`❌ Failed: ${response?.error || "Unknown error"}`);
      }
      
      setTimeout(() => setSmsStatus(""), 3000);
    } catch (error) {
      setSmsStatus("❌ SMS failed");
      setTimeout(() => setSmsStatus(""), 3000);
    }
  };

  if (loading) {
    return (
      <div style={pageStyle}>
        <div style={loadingStyle}>📱 Loading daily updates...</div>
      </div>
    );
  }

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h1 style={titleStyle}>📱 Daily Trading Updates</h1>
        <div style={subtitleStyle}>
          Concise market insights sent to your iPhone • Learning system optimizing over time
        </div>
      </div>

      {/* Current Update - Prominent */}
      {currentUpdate && (
        <div style={currentUpdateStyle}>
          <div style={currentHeaderStyle}>
            <div>
              <div style={currentTitleStyle}>{currentUpdate.title}</div>
              <div style={currentTimeStyle}>{currentUpdate.time}</div>
            </div>
            <button 
              onClick={() => sendSMSUpdate("current")}
              style={smsButtonStyle}
              disabled={smsStatus.includes("Sending")}
            >
              📱 Text Me Now
            </button>
          </div>
          
          <div style={currentSummaryStyle}>{currentUpdate.summary}</div>
          
          <div style={smsPreviewStyle}>
            <div style={smsLabelStyle}>SMS Preview:</div>
            <div style={smsTextStyle}>"{currentUpdate.sms_text}"</div>
          </div>

          {smsStatus && (
            <div style={smsStatusStyle}>{smsStatus}</div>
          )}
        </div>
      )}

      {/* All Updates Timeline */}
      <div style={timelineStyle}>
        <h2 style={timelineHeaderStyle}>📊 Today's Market Schedule</h2>
        
        <div style={timelineGridStyle}>
          {updates.map((update, index) => {
            const isActive = currentUpdate?.type === update.type;
            
            return (
              <div 
                key={update.type} 
                style={{
                  ...updateCardStyle,
                  ...(isActive && activeCardStyle)
                }}
              >
                <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}>{update.title}</div>
                  <div style={cardTimeStyle}>{update.time}</div>
                </div>
                
                <div style={cardSummaryStyle}>{update.summary}</div>
                
                {/* Key Details */}
                {update.details && (
                  <div style={detailsStyle}>
                    {Object.entries(update.details).slice(0, 2).map(([key, value]) => (
                      <div key={key} style={detailItemStyle}>
                        <span style={detailKeyStyle}>{key.replace('_', ' ')}:</span>
                        <span style={detailValueStyle}>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Items */}
                {update.action_items && update.action_items.length > 0 && (
                  <div style={actionItemsStyle}>
                    {update.action_items.slice(0, 2).map((item, i) => (
                      <div key={i} style={actionItemStyle}>• {item}</div>
                    ))}
                  </div>
                )}

                <button 
                  onClick={() => sendSMSUpdate(update.type)}
                  style={cardSmsButtonStyle}
                >
                  📱 Send This Update
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Learning System Info */}
      <div style={learningInfoStyle}>
        <h3 style={learningTitleStyle}>🧠 Learning System</h3>
        <div style={learningDescStyle}>
          This system learns from your trading decisions and market outcomes to optimize future recommendations. 
          Updates become more personalized as the system learns your preferences and successful patterns.
        </div>
        <div style={learningStatsStyle}>
          • Tracks decision outcomes over time<br/>
          • Identifies best market timing patterns<br/>
          • Optimizes recommendation accuracy<br/>
          • Personalizes update content
        </div>
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  padding: "20px",
  maxWidth: "1200px",
  margin: "0 auto",
  fontFamily: "ui-sans-serif, system-ui",
  color: "#e7e7e7",
  background: "#000",
  minHeight: "100vh"
};

const headerStyle: React.CSSProperties = {
  marginBottom: "30px",
  textAlign: "center"
};

const titleStyle: React.CSSProperties = {
  fontSize: "28px",
  fontWeight: 800,
  margin: "0 0 8px 0",
  color: "#fff"
};

const subtitleStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#999",
  lineHeight: "1.4"
};

const currentUpdateStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #1a1a1a 0%, #111 100%)",
  border: "2px solid #22c55e",
  borderRadius: "16px",
  padding: "24px",
  marginBottom: "40px",
  boxShadow: "0 0 20px rgba(34, 197, 94, 0.1)"
};

const currentHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "16px"
};

const currentTitleStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#22c55e",
  margin: "0 0 4px 0"
};

const currentTimeStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#22c55e",
  opacity: 0.8
};

const currentSummaryStyle: React.CSSProperties = {
  fontSize: "16px",
  color: "#fff",
  marginBottom: "16px",
  lineHeight: "1.4"
};

const smsButtonStyle: React.CSSProperties = {
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  padding: "12px 16px",
  color: "#000",
  fontSize: "14px",
  fontWeight: 700,
  cursor: "pointer",
  whiteSpace: "nowrap"
};

const smsPreviewStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "12px",
  marginBottom: "12px"
};

const smsLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#22c55e",
  marginBottom: "4px"
};

const smsTextStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  fontStyle: "italic"
};

const smsStatusStyle: React.CSSProperties = {
  fontSize: "14px",
  padding: "8px",
  borderRadius: "4px",
  background: "#0a0a0a"
};

const timelineStyle: React.CSSProperties = {
  marginBottom: "40px"
};

const timelineHeaderStyle: React.CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#fff",
  marginBottom: "20px"
};

const timelineGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
  gap: "16px"
};

const updateCardStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "16px",
  transition: "all 0.2s ease"
};

const activeCardStyle: React.CSSProperties = {
  borderColor: "#22c55e",
  boxShadow: "0 0 16px rgba(34, 197, 94, 0.1)"
};

const cardHeaderStyle: React.CSSProperties = {
  marginBottom: "8px"
};

const cardTitleStyle: React.CSSProperties = {
  fontSize: "16px",
  fontWeight: 600,
  color: "#fff",
  marginBottom: "2px"
};

const cardTimeStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999"
};

const cardSummaryStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  marginBottom: "12px",
  lineHeight: "1.3"
};

const detailsStyle: React.CSSProperties = {
  marginBottom: "12px"
};

const detailItemStyle: React.CSSProperties = {
  fontSize: "12px",
  marginBottom: "2px",
  display: "flex",
  gap: "8px"
};

const detailKeyStyle: React.CSSProperties = {
  color: "#999",
  minWidth: "80px"
};

const detailValueStyle: React.CSSProperties = {
  color: "#ccc"
};

const actionItemsStyle: React.CSSProperties = {
  marginBottom: "12px"
};

const actionItemStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#999",
  marginBottom: "2px"
};

const cardSmsButtonStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #333",
  borderRadius: "6px",
  padding: "8px 12px",
  color: "#ccc",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  width: "100%"
};

const learningInfoStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: "12px",
  padding: "20px"
};

const learningTitleStyle: React.CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#22c55e",
  marginBottom: "12px"
};

const learningDescStyle: React.CSSProperties = {
  fontSize: "14px",
  color: "#ccc",
  lineHeight: "1.4",
  marginBottom: "12px"
};

const learningStatsStyle: React.CSSProperties = {
  fontSize: "13px",
  color: "#999",
  lineHeight: "1.4"
};

const loadingStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px",
  color: "#999",
  fontSize: "16px"
};