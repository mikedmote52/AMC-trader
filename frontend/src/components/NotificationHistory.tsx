import React from "react";

type Notification = {
  id: string;
  time: string;
  type: "BRIEF" | "ALERT" | "SUMMARY" | "WARNING" | "INFO";
  title: string;
  message: string;
  status: "SENT" | "FAILED" | "PENDING";
  channel: "SMS" | "DASHBOARD" | "BOTH";
  importance: "HIGH" | "MEDIUM" | "LOW";
};

type NotificationHistoryProps = {
  notifications: Notification[];
  isLoading?: boolean;
};

export default function NotificationHistory({ notifications, isLoading }: NotificationHistoryProps) {
  if (isLoading) {
    return (
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={titleStyle}>📱 RECENT NOTIFICATIONS</span>
          <div style={loadingBadgeStyle}>Loading...</div>
        </div>
        <div style={loadingContentStyle}>
          Loading notification history...
        </div>
      </div>
    );
  }

  const getTypeInfo = (type: Notification["type"]) => {
    switch (type) {
      case "BRIEF":
        return { icon: "📈", color: "#3b82f6", label: "Daily Brief" };
      case "ALERT":
        return { icon: "🚨", color: "#ef4444", label: "Alert" };
      case "SUMMARY":
        return { icon: "📊", color: "#22c55e", label: "Summary" };
      case "WARNING":
        return { icon: "⚠️", color: "#f59e0b", label: "Warning" };
      case "INFO":
        return { icon: "ℹ️", color: "#6b7280", label: "Info" };
      default:
        return { icon: "📝", color: "#9ca3af", label: "Unknown" };
    }
  };

  const getStatusInfo = (status: Notification["status"]) => {
    switch (status) {
      case "SENT":
        return { icon: "✅", color: "#22c55e", label: "Sent" };
      case "FAILED":
        return { icon: "❌", color: "#ef4444", label: "Failed" };
      case "PENDING":
        return { icon: "🕐", color: "#f59e0b", label: "Pending" };
      default:
        return { icon: "❓", color: "#9ca3af", label: "Unknown" };
    }
  };

  const getChannelInfo = (channel: Notification["channel"]) => {
    switch (channel) {
      case "SMS":
        return { icon: "💬", color: "#8b5cf6", label: "SMS" };
      case "DASHBOARD":
        return { icon: "💻", color: "#06b6d4", label: "Dashboard" };
      case "BOTH":
        return { icon: "📱", color: "#10b981", label: "Both" };
      default:
        return { icon: "❓", color: "#9ca3af", label: "Unknown" };
    }
  };

  const getImportanceColor = (importance: Notification["importance"]) => {
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
        <span style={titleStyle}>📱 RECENT NOTIFICATIONS</span>
        <div style={countBadgeStyle}>
          {notifications.length} Recent
        </div>
      </div>

      <div style={notificationListStyle}>
        {notifications.map((notification) => {
          const typeInfo = getTypeInfo(notification.type);
          const statusInfo = getStatusInfo(notification.status);
          const channelInfo = getChannelInfo(notification.channel);
          const importanceColor = getImportanceColor(notification.importance);

          return (
            <div key={notification.id} style={notificationItemStyle}>
              <div style={notificationHeaderStyle}>
                <div style={typeAndTimeStyle}>
                  <div style={typeIconStyle(typeInfo.color)}>
                    {typeInfo.icon}
                  </div>
                  <div style={timeAndTypeStyle}>
                    <span style={timeStyle}>{notification.time}</span>
                    <span style={typeStyle}>{typeInfo.label}</span>
                  </div>
                </div>

                <div style={badgesStyle}>
                  <div style={importanceBadgeStyle(importanceColor)}>
                    {notification.importance}
                  </div>
                  <div style={channelBadgeStyle(channelInfo.color)}>
                    {channelInfo.icon} {channelInfo.label}
                  </div>
                  <div style={statusBadgeStyle(statusInfo.color)}>
                    {statusInfo.icon} {statusInfo.label}
                  </div>
                </div>
              </div>

              <div style={notificationContentStyle}>
                <div style={titleNotificationStyle}>
                  {notification.title}
                </div>
                <div style={messageStyle}>
                  {notification.message}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {notifications.length === 0 && (
        <div style={emptyStateStyle}>
          <div>No recent notifications</div>
          <div style={emptySubtextStyle}>Notifications will appear here as they're sent</div>
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

const countBadgeStyle: React.CSSProperties = {
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

const notificationListStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const notificationItemStyle: React.CSSProperties = {
  background: "#111",
  border: "1px solid #333",
  borderRadius: 12,
  padding: 16,
};

const notificationHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: 12,
};

const typeAndTimeStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
};

const typeIconStyle = (color: string): React.CSSProperties => ({
  fontSize: 20,
  background: `${color}20`,
  border: `1px solid ${color}50`,
  borderRadius: 8,
  padding: 8,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
});

const timeAndTypeStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
};

const timeStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: "#eee",
};

const typeStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#999",
};

const badgesStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  alignItems: "center",
};

const importanceBadgeStyle = (color: string): React.CSSProperties => ({
  background: `${color}20`,
  border: `1px solid ${color}30`,
  borderRadius: 6,
  padding: "2px 6px",
  fontSize: 10,
  fontWeight: 600,
  color: color,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
});

const channelBadgeStyle = (color: string): React.CSSProperties => ({
  background: `${color}20`,
  border: `1px solid ${color}30`,
  borderRadius: 6,
  padding: "2px 6px",
  fontSize: 10,
  fontWeight: 600,
  color: color,
  display: "flex",
  alignItems: "center",
  gap: 2,
});

const statusBadgeStyle = (color: string): React.CSSProperties => ({
  background: `${color}20`,
  border: `1px solid ${color}30`,
  borderRadius: 6,
  padding: "2px 6px",
  fontSize: 10,
  fontWeight: 600,
  color: color,
  display: "flex",
  alignItems: "center",
  gap: 2,
});

const notificationContentStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
};

const titleNotificationStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 600,
  color: "#eee",
  lineHeight: 1.3,
};

const messageStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#bbb",
  lineHeight: 1.4,
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