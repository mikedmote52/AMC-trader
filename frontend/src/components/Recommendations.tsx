import React, { useState } from 'react';
import { API_BASE } from '../config';
import { usePolling } from '../hooks/usePolling';
import RecommendationCard from './RecommendationCard';
import TradeModal from './TradeModal';

export function Recommendations() {
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [showTradeModal, setShowTradeModal] = useState(false);
  
  const { data, error, isLoading } = usePolling<any>(`${API_BASE}/discovery/contenders`, 15000);
  
  // Handle both array and {items: [...]} response formats
  const items = Array.isArray(data) ? data : (data?.items || []);
  
  // Sort by score descending
  const sortedItems = [...items].sort((a, b) => (b.score || 0) - (a.score || 0));

  const handleOpenTradeModal = (candidate: any) => {
    setSelectedCandidate(candidate);
    setShowTradeModal(true);
  };

  const handleCloseTradeModal = () => {
    setShowTradeModal(false);
    setSelectedCandidate(null);
  };

  if (isLoading && !items.length) {
    return (
      <div className="recommendations">
        <h2>Recommendations</h2>
        <div className="loading">Loading recommendations...</div>
      </div>
    );
  }

  return (
    <div className="recommendations">
      <h2>Recommendations</h2>
      
      {error && (
        <div className="error-banner">
          ❌ Failed to fetch recommendations: {error.message}
        </div>
      )}
      
      {sortedItems.length > 0 ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedItems.map((item: any) => (
            <RecommendationCard 
              key={item.symbol} 
              item={item} 
              onOpenTradeModal={handleOpenTradeModal}
            />
          ))}
        </div>
      ) : !error && (
        <div className="opacity-70 italic">No recommendations available</div>
      )}

      {showTradeModal && selectedCandidate && (
        <TradeModal
          candidate={selectedCandidate}
          onClose={handleCloseTradeModal}
        />
      )}
    </div>
  );
}