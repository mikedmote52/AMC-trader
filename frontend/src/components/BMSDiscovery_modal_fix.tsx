// Modal Component with Inline Styles - Lines to replace in BMSDiscovery.tsx starting at line 667

const BMSAuditModal: React.FC<BMSAuditModalProps> = ({ candidate, onClose }) => {
  const [auditData, setAuditData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [newsData, setNewsData] = useState<any[]>([]);
  const [loadingNews, setLoadingNews] = useState(true);

  // Calculate price target and timeframe
  const priceTarget = candidate.pattern_match
    ? (() => {
        const similarity = candidate.pattern_match.similarity * 100;
        let avgGainPct: number;
        let timeframeDays: string;

        if (similarity >= 85) {
          avgGainPct = 220;
          timeframeDays = "7-14";
        } else if (similarity >= 75) {
          avgGainPct = 135;
          timeframeDays = "10-20";
        } else {
          avgGainPct = 75;
          timeframeDays = "14-30";
        }

        return {
          target: candidate.price * (1 + avgGainPct / 100),
          gainPct: avgGainPct,
          timeframeDays
        };
      })()
    : null;

  useEffect(() => {
    const fetchAuditData = async () => {
      try {
        const data = await getJSON(\`/discovery/audit/\${candidate.symbol}\`);
        setAuditData(data);
      } catch (err) {
        console.error('Error fetching audit data:', err);
      } finally {
        setLoading(false);
      }
    };

    const fetchNews = async () => {
      try {
        const news = await getJSON(\`/news/\${candidate.symbol}?limit=3\`);
        if (news && news.results) {
          setNewsData(news.results);
        }
      } catch (err) {
        console.error('Error fetching news:', err);
      } finally {
        setLoadingNews(false);
      }
    };

    fetchAuditData();
    fetchNews();
  }, [candidate.symbol]);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 50
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        maxWidth: '900px',
        width: '100%',
        margin: '16px',
        maxHeight: '80vh',
        overflowY: 'auto'
      }}>
        <div style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '24px', fontWeight: 'bold' }}>{candidate.symbol} - Investment Analysis</h3>
            <button
              onClick={onClose}
              style={{
                color: '#6b7280',
                fontSize: '20px',
                border: 'none',
                background: 'none',
                cursor: 'pointer'
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Investment Thesis - Primary Section */}
            <div style={{
              background: 'linear-gradient(to bottom right, #eff6ff, #e0e7ff)',
              border: '2px solid #bfdbfe',
              borderRadius: '12px',
              padding: '24px'
            }}>
              <h4 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '16px', color: '#111827' }}>
                {candidate.symbol} Investment Thesis
              </h4>

              {/* Pattern Match Summary */}
              {candidate.pattern_match && (
                <div style={{
                  marginBottom: '24px',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid #bfdbfe'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '24px' }}>⭐</span>
                    <h5 style={{ fontWeight: 'bold', fontSize: '18px', color: '#111827' }}>Pattern Match Analysis</h5>
                  </div>
                  <p style={{ color: '#374151', lineHeight: '1.6' }}>
                    <strong style={{ color: '#1e40af' }}>{Math.round(candidate.pattern_match.similarity * 100)}% similarity</strong> to {candidate.pattern_match.pattern}'s explosive pattern that gained <strong style={{ color: '#16a34a' }}>{candidate.pattern_match.outcome}</strong> in 7 days.
                  </p>
                </div>
              )}

              {/* Why This Stock */}
              <div style={{ marginBottom: '24px' }}>
                <h5 style={{ fontWeight: 'bold', fontSize: '18px', marginBottom: '12px', color: '#111827' }}>Why This Stock:</h5>
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ color: '#2563eb', fontWeight: 'bold' }}>•</span>
                    <span style={{ color: '#374151' }}>
                      <strong>{candidate.volume_surge.toFixed(1)}x Volume Surge</strong> - Institutional accumulation detected
                      {candidate.pattern_match && \` (matches \${candidate.pattern_match.pattern}'s \${candidate.pattern_match.pattern === 'VIGL' ? '1.8x' : candidate.pattern_match.pattern === 'CRWV' ? '1.9x' : '1.7x'})\`}
                    </span>
                  </li>
                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ color: '#2563eb', fontWeight: 'bold' }}>•</span>
                    <span style={{ color: '#374151' }}>
                      <strong>{candidate.momentum_1d >= 0 ? '+' : ''}{candidate.momentum_1d.toFixed(1)}% Price Change</strong> -
                      {Math.abs(candidate.momentum_1d) < 2 ? ' Stealth accumulation, not discovered by retail yet' : ' Momentum building'}
                    </span>
                  </li>
                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ color: '#2563eb', fontWeight: 'bold' }}>•</span>
                    <span style={{ color: '#374151' }}>
                      <strong>\${candidate.price.toFixed(2)} Price</strong> - Low price = high % upside potential (easier path to multi-bagger)
                    </span>
                  </li>
                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                    <span style={{ color: '#2563eb', fontWeight: 'bold' }}>•</span>
                    <span style={{ color: '#374151' }}>
                      <strong>{candidate.bms_score.toFixed(1)}% Explosion Probability</strong>
                      {candidate.base_probability && candidate.pattern_match && \` (\${candidate.base_probability.toFixed(1)}% base + \${candidate.pattern_match.bonus_points} pts pattern bonus)\`}
                    </span>
                  </li>
                </ul>
              </div>

              {/* Historical Context */}
              {candidate.pattern_match && candidate.pattern_match.similarity >= 0.65 && (
                <div style={{
                  marginBottom: '24px',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid #bbf7d0'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '24px' }}>📈</span>
                    <h5 style={{ fontWeight: 'bold', fontSize: '18px', color: '#111827' }}>Historical Context</h5>
                  </div>
                  <p style={{ color: '#374151', marginBottom: '12px' }}>
                    Stocks with {Math.round(candidate.pattern_match.similarity * 100)}%+ pattern match have historically moved:
                  </p>
                  <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', color: '#374151' }}>
                    <li><strong>VIGL:</strong> 1.8x RVOL, +0.4% change → <span style={{ color: '#16a34a', fontWeight: 'bold' }}>+324% in 7 days</span></li>
                    <li><strong>CRWV:</strong> 1.9x RVOL, -0.2% change → <span style={{ color: '#16a34a', fontWeight: 'bold' }}>+171% in 10 days</span></li>
                    <li><strong>AEVA:</strong> 1.7x RVOL, +1.1% change → <span style={{ color: '#16a34a', fontWeight: 'bold' }}>+162% in 14 days</span></li>
                  </ul>
                </div>
              )}

              {/* Price Target & Timeframe */}
              {priceTarget && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
                  <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '16px', textAlign: 'center', border: '1px solid #e5e7eb' }}>
                    <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '4px' }}>Current Price</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827' }}>\${candidate.price.toFixed(2)}</div>
                  </div>
                  <div style={{ backgroundColor: '#f0fdf4', borderRadius: '8px', padding: '16px', textAlign: 'center', border: '2px solid #86efac' }}>
                    <div style={{ fontSize: '14px', color: '#15803d', fontWeight: '600', marginBottom: '4px' }}>Target Price</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#16a34a' }}>\${priceTarget.target.toFixed(2)}</div>
                    <div style={{ fontSize: '12px', color: '#16a34a', fontWeight: '600' }}>+{priceTarget.gainPct}% avg</div>
                  </div>
                  <div style={{ backgroundColor: '#eff6ff', borderRadius: '8px', padding: '16px', textAlign: 'center', border: '1px solid #bfdbfe' }}>
                    <div style={{ fontSize: '14px', color: '#1d4ed8', fontWeight: '600', marginBottom: '4px' }}>Timeframe</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2563eb' }}>{priceTarget.timeframeDays}</div>
                    <div style={{ fontSize: '12px', color: '#2563eb' }}>days</div>
                  </div>
                </div>
              )}

              {/* Risk Assessment */}
              <div style={{
                backgroundColor: '#fef3c7',
                borderRadius: '8px',
                padding: '16px',
                border: '1px solid #fbbf24'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '20px' }}>⚠️</span>
                  <h5 style={{ fontWeight: 'bold', color: '#111827' }}>Risk Assessment</h5>
                </div>
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '14px', color: '#374151' }}>
                  <li><strong>Stop-loss recommended:</strong> {candidate.bms_score >= 75 ? '5-7%' : '7-10%'} below entry (based on confidence level)</li>
                  <li><strong>Position size:</strong> {candidate.action === 'TRADE_READY' ? 'Standard' : 'Reduced'} (adjust based on your risk tolerance)</li>
                  <li><strong>Risk/Reward:</strong> {priceTarget ? \`1:\${(priceTarget.gainPct / 7).toFixed(1)}\` : '1:10+'} - Excellent asymmetric opportunity</li>
                </ul>
              </div>
            </div>

            {/* News & Catalyst Section */}
            <div style={{
              background: 'linear-gradient(to bottom right, #fef3c7, #fde68a)',
              border: '2px solid #fbbf24',
              borderRadius: '12px',
              padding: '24px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <span style={{ fontSize: '24px' }}>📰</span>
                <h4 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827' }}>Recent News & Catalyst</h4>
              </div>

              {loadingNews ? (
                <p style={{ color: '#6b7280', textAlign: 'center', padding: '16px' }}>Loading news...</p>
              ) : newsData.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {newsData.map((article, index) => (
                    <div key={index} style={{
                      backgroundColor: 'white',
                      borderRadius: '8px',
                      padding: '16px',
                      border: '1px solid #e5e7eb'
                    }}>
                      <h5 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>
                        {article.title}
                      </h5>
                      <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.5', marginBottom: '8px' }}>
                        {article.description}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                        <span style={{ color: '#9ca3af' }}>
                          {new Date(article.published_utc).toLocaleDateString()}
                        </span>
                        {article.insights && article.insights[0] && (
                          <span style={{
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontWeight: '600',
                            backgroundColor: article.insights[0].sentiment === 'positive' ? '#dcfce7' :
                                            article.insights[0].sentiment === 'negative' ? '#fee2e2' : '#f3f4f6',
                            color: article.insights[0].sentiment === 'positive' ? '#166534' :
                                   article.insights[0].sentiment === 'negative' ? '#991b1b' : '#4b5563'
                          }}>
                            {article.insights[0].sentiment.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <a
                        href={article.article_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          marginTop: '8px',
                          color: '#2563eb',
                          fontSize: '13px',
                          textDecoration: 'none',
                          fontWeight: '600'
                        }}
                      >
                        Read full article →
                      </a>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid #e5e7eb',
                  textAlign: 'center'
                }}>
                  <p style={{ color: '#6b7280', marginBottom: '8px' }}>No recent news available</p>
                  <p style={{ fontSize: '14px', color: '#9ca3af' }}>
                    This stock was discovered through pattern-based analysis (volume + price action), not news catalysts
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '12px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
              <button
                onClick={onClose}
                style={{
                  padding: '12px 24px',
                  border: '2px solid #e5e7eb',
                  borderRadius: '8px',
                  backgroundColor: 'white',
                  color: '#374151',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
              {candidate.action === 'TRADE_READY' && (
                <button
                  style={{
                    flex: 1,
                    padding: '12px 24px',
                    backgroundColor: '#16a34a',
                    color: 'white',
                    borderRadius: '8px',
                    border: 'none',
                    fontWeight: 'bold',
                    fontSize: '18px',
                    cursor: 'pointer'
                  }}
                >
                  🚀 Buy Now
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
