import React from "react";

type TimelineEvent = {
  time: string;
  status: "COMPLETED" | "IN_PROGRESS" | "PENDING" | "SCHEDULED";
  title: string;
  description: string;
  importance: "HIGH" | "MEDIUM" | "LOW";
};

type DailyTimelineViewProps = {
  events: TimelineEvent[];
  isLoading?: boolean;
};

export default function DailyTimelineView({ events, isLoading }: DailyTimelineViewProps) {
  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={titleStyle}>⏰ TODAY'S TIMELINE</span>
          <div style={loadingBadgeStyle}>Loading...</div>
        </div>
        <div style={loadingContentStyle}>
          Loading timeline events...
        </div>
      </div>
    );
  }

  const getStatusInfo = (status: TimelineEvent["status"]) => {
    switch (status) {
      case "COMPLETED":
        return { icon: "✅", color: "#22c55e", bgColor: "rgba(34, 197, 94, 0.1)" };
      case "IN_PROGRESS":
        return { icon: "🔄", color: "#f59e0b", bgColor: "rgba(245, 158, 11, 0.1)" };
      case "PENDING":
        return { icon: "⏳", color: "#3b82f6", bgColor: "rgba(59, 130, 246, 0.1)" };
      case "SCHEDULED":
        return { icon: "📅", color: "#9ca3af", bgColor: "rgba(156, 163, 175, 0.1)" };
      default:
        return { icon: "❓", color: "#666", bgColor: "rgba(102, 102, 102, 0.1)" };
    }
  };

  const getImportanceColor = (importance: TimelineEvent["importance"]) => {
    switch (importance) {
      case "HIGH":
        return "#ef4444";
      case "MEDIUM":
        return "#f59e0b";
      case "LOW":
        return "#22c55e";
      default:
        return "#9ca3af";
    }
  };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>⏰ TODAY'S TIMELINE</span>
        <div style={eventCountBadgeStyle}>
          {events.length} Events
        </div>
      </div>

      <div style={timelineListStyle}>
        {events.map((event, index) => {
          const statusInfo = getStatusInfo(event.status);
          const importanceColor = getImportanceColor(event.importance);
          
          return (
            <div key={index} style={timelineItemStyle}>
              <div style={timeIndicatorStyle}>
                <div style={timeStyle}>{event.time}</div>
                <div 
                  style={{
                    ...statusIconStyle,
                    color: statusInfo.color,
                    background: statusInfo.bgColor,
                    border: `1px solid ${statusInfo.color}30`
                  }}
                >
                  {statusInfo.icon}
                </div>
              </div>

              <div style={eventContentStyle}>
                <div style={eventHeaderStyle}>
                  <span style={eventTitleStyle}>{event.title}</span>
                  <div 
                    style={{
                      ...importanceBadgeStyle,
                      color: importanceColor,
                      background: `${importanceColor}20`,
                      border: `1px solid ${importanceColor}30`
                    }}
                  >
                    {event.importance}
                  </div>
                </div>
                
                <div style={eventDescriptionStyle}>
                  {event.description}
                </div>

                <div 
                  style={{
                    ...eventStatusStyle,
                    color: statusInfo.color
                  }}
                >
                  {event.status.replace('_', ' ').toLowerCase()}
                </div>
              </div>

              {index < events.length - 1 && <div style={timelineConnectorStyle}></div>}
            </div>
          );
        })}
      </div>

      {events.length === 0 && (
        <div style={emptyStateStyle}>
          <div>No events scheduled for today</div>
          <div style={emptySubtextStyle}>Timeline will update as market events occur</div>
        </div>
      )}
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  background: "#0a0a0a",
  border: "1px solid #333",
  borderRadius: 16,
  padding: 20,
  marginBottom: 24,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 20,
};

const titleStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 700,
  color: "#eee",
};

const loadingBadgeStyle: React.CSSProperties = {
  background: "rgba(59, 130, 246, 0.2)",
  border: "1px solid rgba(59, 130, 246, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: "#3b82f6",
};

const eventCountBadgeStyle: React.CSSProperties = {
  background: "rgba(156, 163, 175, 0.2)",
  border: "1px solid rgba(156, 163, 175, 0.5)",
  borderRadius: 8,
  padding: "4px 8px",
  fontSize: 11,
  fontWeight: 600,
  color: "#9ca3af",
};

const loadingContentStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
  padding: 20,
};

const timelineListStyle: React.CSSProperties = {
  position: "relative",
};

const timelineItemStyle: React.CSSProperties = {
  display: "flex",
  gap: 20,
  marginBottom: 20,
  position: "relative",
};

const timeIndicatorStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: 8,
  minWidth: 80,
};

const timeStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#eee",
  textAlign: "center",
  minWidth: 60,
};

const statusIconStyle: React.CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: "50%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 14,
  fontWeight: 600,
};

const eventContentStyle: React.CSSProperties = {
  flex: 1,
  background: "#111",
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
};

const eventHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 8,
};

const eventTitleStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 600,
  color: "#eee",
};

const importanceBadgeStyle: React.CSSProperties = {
  borderRadius: 6,
  padding: "2px 6px",
  fontSize: 10,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const eventDescriptionStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#bbb",
  lineHeight: 1.4,
  marginBottom: 8,
};

const eventStatusStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  textTransform: "capitalize",
};

const timelineConnectorStyle: React.CSSProperties = {
  position: "absolute",
  left: 119, // 80px (timeIndicator width) + 20px (gap) + 19px (half of statusIcon)
  top: 52, // Approximate position after time and icon
  width: 2,
  height: 20,
  background: "#333",
};

const emptyStateStyle: React.CSSProperties = {
  textAlign: "center",
  color: "#999",
  fontSize: 14,
  padding: 20,
};

const emptySubtextStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#666",
  marginTop: 4,
};