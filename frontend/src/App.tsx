import React from "react";
import Recommendations from "./components/Recommendations";
import Holdings from "./components/Holdings";

export default function App() {
  return (
    <div style={{padding:16, maxWidth:1400, margin:"0 auto", fontFamily:"ui-sans-serif, system-ui", color:"#e7e7e7"}}>
      <h2 style={{margin:"6px 0 14px"}}>Squeeze Candidates</h2>
      <Recommendations />
      <h2 style={{margin:"22px 0 14px"}}>Your Holdings</h2>
      <Holdings />
    </div>
  );
}