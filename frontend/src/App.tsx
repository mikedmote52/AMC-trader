import React, { useState } from "react";
import Recommendations from "./components/Recommendations";
import Holdings from "./components/Holdings";
import DebugBadge from "./components/DebugBadge";

export default function App() {
  const [debugInfo, setDebugInfo] = useState({
    holdingsStatus: "loading",
    holdingsCount: 0,
    contendersStatus: "loading", 
    contendersRaw: 0,
    contendersFiltered: 0,
    lastUpdated: new Date().toLocaleTimeString()
  });

  return (
    <div style={{padding:16, maxWidth:1400, margin:"0 auto", fontFamily:"ui-sans-serif, system-ui", color:"#e7e7e7"}}>
      <h2 style={{margin:"6px 0 14px"}}>Squeeze Candidates</h2>
      <Recommendations onDebugUpdate={(info) => setDebugInfo(prev => ({...prev, ...info}))} />
      <h2 style={{margin:"22px 0 14px"}}>Your Holdings</h2>
      <Holdings onDebugUpdate={(info) => setDebugInfo(prev => ({...prev, ...info}))} />
      <DebugBadge {...debugInfo} />
    </div>
  );
}