import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";

export default function Navigation() {
  return <NavigationWithResponsive />;
}

const navStyle: React.CSSProperties = {
  background: "#111",
  borderBottom: "1px solid #333",
  marginBottom: "20px",
  position: "sticky",
  top: 0,
  zIndex: 100
};

const desktopNavStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  padding: "12px 20px",
  gap: "8px"
};

const mobileNavStyle: React.CSSProperties = {
  display: "none",
  position: "relative",
  padding: "12px 20px"
};

const navLinkStyle: React.CSSProperties = {
  display: "block",
  padding: "8px 16px",
  color: "#ccc",
  textDecoration: "none",
  borderRadius: "8px",
  fontSize: "14px",
  fontWeight: 600,
  transition: "all 0.2s ease",
  border: "1px solid transparent"
};

const activeNavLinkStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  color: "#000",
  boxShadow: "0 2px 8px rgba(34, 197, 94, 0.2)"
};

const hamburgerStyle: React.CSSProperties = {
  background: "transparent",
  border: "1px solid #333",
  borderRadius: "8px",
  padding: "8px 12px",
  color: "#ccc",
  fontSize: "16px",
  cursor: "pointer"
};

const mobileMenuStyle: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  left: 0,
  right: 0,
  background: "#111",
  border: "1px solid #333",
  borderTop: "none",
  borderRadius: "0 0 8px 8px",
  display: "flex",
  flexDirection: "column",
  padding: "8px"
};

const mobileNavLinkStyle: React.CSSProperties = {
  display: "block",
  padding: "12px 16px",
  color: "#ccc",
  textDecoration: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: 600,
  margin: "2px 0"
};

const activeMobileNavLinkStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  color: "#000"
};

// Add responsive styles with media query
const style = document.createElement('style');
style.textContent = `
@media (max-width: 768px) {
  [data-desktop-nav] { display: none !important; }
  [data-mobile-nav] { display: block !important; }
}
@media (min-width: 769px) {
  [data-desktop-nav] { display: flex !important; }
  [data-mobile-nav] { display: none !important; }
}
`;
document.head.appendChild(style);

// Update the component to use data attributes
export function NavigationWithResponsive() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Home", icon: "🏠" },
    { path: "/squeeze", label: "Squeeze Monitor", icon: "🔍" },
    { path: "/discovery", label: "Discovery", icon: "🎯" },
    { path: "/portfolio", label: "Portfolio", icon: "📊" },
    { path: "/updates", label: "Daily Updates", icon: "📱" }
  ];

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);

  return (
    <nav style={navStyle}>
      {/* Desktop Navigation */}
      <div data-desktop-nav style={desktopNavStyle}>
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            style={{
              ...navLinkStyle,
              ...(location.pathname === item.path ? activeNavLinkStyle : {})
            }}
          >
            {item.icon} {item.label}
          </Link>
        ))}
      </div>

      {/* Mobile Navigation */}
      <div data-mobile-nav style={mobileNavStyle}>
        <button onClick={toggleMenu} style={hamburgerStyle}>
          {isMenuOpen ? "✕" : "☰"}
        </button>
        
        {isMenuOpen && (
          <div style={mobileMenuStyle}>
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  ...mobileNavLinkStyle,
                  ...(location.pathname === item.path ? activeMobileNavLinkStyle : {})
                }}
                onClick={() => setIsMenuOpen(false)}
              >
                {item.icon} {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}