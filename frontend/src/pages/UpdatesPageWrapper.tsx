import React from "react";
import UpdatesPage from "../components/UpdatesPage";

export default function UpdatesPageWrapper() {
  return (
    <div style={wrapperStyle}>
      <UpdatesPage />
    </div>
  );
}

const wrapperStyle: React.CSSProperties = {
  // Remove the padding since UpdatesPage already has its own
  margin: 0,
  minHeight: "calc(100vh - 60px)" // Account for navigation height
};