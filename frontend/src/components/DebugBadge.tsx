import React from "react";

type DebugInfo = {
  holdingsStatus: string;
  holdingsCount: number;
  contendersStatus: string;
  contendersRaw: number;
  contendersFiltered: number;
  lastUpdated: string;
};

export default function DebugBadge({ 
  holdingsStatus, 
  holdingsCount, 
  contendersStatus, 
  contendersRaw, 
  contendersFiltered, 
  lastUpdated 
}: DebugInfo) {
  return (
    <div style={{
      position: "fixed",
      bottom: 16,
      right: 16,
      background: "#000",
      color: "#0f0",
      padding: "8px 12px",
      borderRadius: 8,
      fontSize: 11,
      fontFamily: "monospace",
      border: "1px solid #333",
      zIndex: 9999,
      maxWidth: 200,
      lineHeight: 1.3
    }}>
      <div><strong>Holdings:</strong> {holdingsStatus} ({holdingsCount})</div>
      <div><strong>Contenders:</strong> {contendersStatus}</div>
      <div>{contendersRaw}→{contendersFiltered} after ETF filter</div>
      <div><strong>Updated:</strong> {lastUpdated}</div>
    </div>
  );
}