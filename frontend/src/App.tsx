import React from "react";
import NotificationDashboard from "./components/NotificationDashboard";
import Recommendations from "./components/Recommendations";
import Holdings from "./components/Holdings";
import MarketStatus from "./components/MarketStatus";

export default function App() {
  return (
    <div style={{fontFamily:"ui-sans-serif, system-ui", color:"#e7e7e7", background:"#000"}}>
      {/* Primary Dashboard Interface */}
      <NotificationDashboard />
      
      {/* Divider */}
      <div style={{margin:"48px 0", borderTop:"2px solid #333", position:"relative"}}>
        <div style={{
          position:"absolute", 
          top:"-12px", 
          left:"50%", 
          transform:"translateX(-50%)", 
          background:"#000", 
          padding:"0 16px", 
          color:"#666", 
          fontSize:"14px",
          fontWeight:600
        }}>
          LEGACY INTERFACE
        </div>
      </div>
      
      {/* Legacy Interface */}
      <div className="container-responsive">
        <MarketStatus />
        
        <h2 style={{margin:"6px 0 14px"}}>Squeeze Candidates</h2>
        <Recommendations />
        
        <h2 style={{margin:"22px 0 14px"}}>Your Holdings</h2>
        <Holdings />
      </div>
    </div>
  );
}