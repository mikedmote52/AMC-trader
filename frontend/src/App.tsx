import React from "react";
import Recommendations from "./components/Recommendations";
import Holdings from "./components/Holdings";
import MarketStatus from "./components/MarketStatus";

export default function App() {
  return (
    <div className="container-responsive" style={{fontFamily:"ui-sans-serif, system-ui", color:"#e7e7e7"}}>
      <MarketStatus />
      
      <h2 style={{margin:"6px 0 14px"}}>Squeeze Candidates</h2>
      <Recommendations />
      
      <h2 style={{margin:"22px 0 14px"}}>Your Holdings</h2>
      <Holdings />
    </div>
  );
}