import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navigation from "./components/Navigation";
import HomePage from "./pages/HomePage";
import BMSDiscoveryPage from "./pages/BMSDiscoveryPage";
import PortfolioPage from "./pages/PortfolioPage";
import UpdatesPageWrapper from "./pages/UpdatesPageWrapper";

export default function App() {
  return (
    <Router>
      <div style={{
        fontFamily: "ui-sans-serif, system-ui", 
        color: "#e7e7e7", 
        background: "#000",
        minHeight: "100vh"
      }}>
        <Navigation />
        
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/squeeze" element={<BMSDiscoveryPage />} />
          <Route path="/discovery" element={<BMSDiscoveryPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/updates" element={<UpdatesPageWrapper />} />
        </Routes>
      </div>
    </Router>
  );
}

