import { Holdings } from './components/Holdings'
import { Recommendations } from './components/Recommendations'
import { RiskBar } from './components/RiskBar'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Trading Dashboard</h1>
      </header>
      
      <main className="app-main">
        <div className="dashboard-grid">
          <div className="risk-section">
            <RiskBar />
          </div>
          
          <div className="holdings-section">
            <Holdings />
          </div>
          
          <div className="recommendations-section">
            <Recommendations />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
