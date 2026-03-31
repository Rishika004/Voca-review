"use client";

import { useState } from "react";

interface CustomerData {
  conversation_id: string;
  user_id: string;
  timestamp: string;
  intent: string;
  product_category: string;
  resolution_status: string;
  feedback_rating: number;
  user_sentiment: string;
}

export default function CustomersPage() {
  const [customers] = useState<CustomerData[]>([
    {
      conversation_id: "conv_001",
      user_id: "user_12345",
      timestamp: "2025-07-14 09:15:32",
      intent: "Product Inquiry",
      product_category: "Electronics",
      resolution_status: "Resolved",
      feedback_rating: 5,
      user_sentiment: "Positive",
    },
    {
      conversation_id: "conv_002",
      user_id: "user_67890",
      timestamp: "2025-07-14 10:22:18",
      intent: "Technical Support",
      product_category: "Software",
      resolution_status: "Pending",
      feedback_rating: 3,
      user_sentiment: "Neutral",
    },
    {
      conversation_id: "conv_003",
      user_id: "user_24681",
      timestamp: "2025-07-14 11:45:09",
      intent: "Billing Issue",
      product_category: "Subscription",
      resolution_status: "Resolved",
      feedback_rating: 4,
      user_sentiment: "Positive",
    },
    {
      conversation_id: "conv_004",
      user_id: "user_13579",
      timestamp: "2025-07-14 13:30:45",
      intent: "Return Request",
      product_category: "Clothing",
      resolution_status: "In Progress",
      feedback_rating: 2,
      user_sentiment: "Negative",
    },
    {
      conversation_id: "conv_005",
      user_id: "user_97531",
      timestamp: "2025-07-14 14:18:23",
      intent: "Product Inquiry",
      product_category: "Home & Garden",
      resolution_status: "Resolved",
      feedback_rating: 5,
      user_sentiment: "Positive",
    },
    {
      conversation_id: "conv_006",
      user_id: "user_86420",
      timestamp: "2025-07-14 15:07:56",
      intent: "Complaint",
      product_category: "Electronics",
      resolution_status: "Escalated",
      feedback_rating: 1,
      user_sentiment: "Negative",
    },
    {
      conversation_id: "conv_007",
      user_id: "user_75319",
      timestamp: "2025-07-14 16:25:14",
      intent: "General Inquiry",
      product_category: "Books",
      resolution_status: "Resolved",
      feedback_rating: 4,
      user_sentiment: "Positive",
    },
    {
      conversation_id: "conv_008",
      user_id: "user_64208",
      timestamp: "2025-07-14 17:33:27",
      intent: "Technical Support",
      product_category: "Software",
      resolution_status: "Pending",
      feedback_rating: 3,
      user_sentiment: "Neutral",
    },
    {
      conversation_id: "conv_009",
      user_id: "user_53107",
      timestamp: "2025-07-14 18:12:08",
      intent: "Product Inquiry",
      product_category: "Sports",
      resolution_status: "Resolved",
      feedback_rating: 5,
      user_sentiment: "Positive",
    },
    {
      conversation_id: "conv_010",
      user_id: "user_42096",
      timestamp: "2025-07-14 19:45:33",
      intent: "Order Status",
      product_category: "Electronics",
      resolution_status: "In Progress",
      feedback_rating: 4,
      user_sentiment: "Neutral",
    },
  ]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Resolved":
        return "#4CAF50";
      case "Pending":
        return "#FF9800";
      case "In Progress":
        return "#2196F3";
      case "Escalated":
        return "#f44336";
      default:
        return "#757575";
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "Positive":
        return "#4CAF50";
      case "Neutral":
        return "#FF9800";
      case "Negative":
        return "#f44336";
      default:
        return "#757575";
    }
  };

  const getRatingStars = (rating: number) => {
    return "★".repeat(rating) + "☆".repeat(5 - rating);
  };

  return (
    <div
      style={{
        fontFamily: "sans-serif",
        padding: "20px",
        maxWidth: "1400px",
        margin: "auto",
      }}
    >
      <h1 style={{ textAlign: "center", color: "#333", marginBottom: "30px" }}>
        Customer Conversations Dashboard
      </h1>

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          overflow: "hidden",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "14px",
          }}
        >
          <thead>
            <tr style={{ backgroundColor: "#f5f5f5" }}>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Conversation ID
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                User ID
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Timestamp
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Intent
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Product Category
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Resolution Status
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                Feedback Rating
              </th>
              <th
                style={{
                  padding: "12px",
                  textAlign: "left",
                  borderBottom: "2px solid #ddd",
                }}
              >
                User Sentiment
              </th>
            </tr>
          </thead>
          <tbody>
            {customers.map((customer, index) => (
              <tr
                key={customer.conversation_id}
                style={{
                  backgroundColor: index % 2 === 0 ? "#fff" : "#f9f9f9",
                }}
              >
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <code
                    style={{
                      backgroundColor: "#f0f0f0",
                      padding: "2px 4px",
                      borderRadius: "3px",
                    }}
                  >
                    {customer.conversation_id}
                  </code>
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <code
                    style={{
                      backgroundColor: "#f0f0f0",
                      padding: "2px 4px",
                      borderRadius: "3px",
                    }}
                  >
                    {customer.user_id}
                  </code>
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {customer.timestamp}
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <span
                    style={{
                      backgroundColor: "#e3f2fd",
                      color: "#1976d2",
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "500",
                    }}
                  >
                    {customer.intent}
                  </span>
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  {customer.product_category}
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <span
                    style={{
                      backgroundColor:
                        getStatusColor(customer.resolution_status) + "20",
                      color: getStatusColor(customer.resolution_status),
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "500",
                    }}
                  >
                    {customer.resolution_status}
                  </span>
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <span
                    style={{
                      fontSize: "16px",
                      color: "#ff9800",
                    }}
                    title={`${customer.feedback_rating}/5 stars`}
                  >
                    {getRatingStars(customer.feedback_rating)}
                  </span>
                  <span
                    style={{
                      marginLeft: "8px",
                      fontSize: "12px",
                      color: "#666",
                    }}
                  >
                    ({customer.feedback_rating}/5)
                  </span>
                </td>
                <td style={{ padding: "12px", borderBottom: "1px solid #eee" }}>
                  <span
                    style={{
                      backgroundColor:
                        getSentimentColor(customer.user_sentiment) + "20",
                      color: getSentimentColor(customer.user_sentiment),
                      padding: "4px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "500",
                    }}
                  >
                    {customer.user_sentiment}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        style={{
          marginTop: "20px",
          padding: "15px",
          backgroundColor: "#f8f9fa",
          borderRadius: "8px",
          border: "1px solid #e9ecef",
        }}
      >
        <h3 style={{ marginTop: 0, color: "#495057" }}>Summary Statistics</h3>
        <div style={{ display: "flex", gap: "20px", flexWrap: "wrap" }}>
          <div>
            <strong>Total Conversations:</strong> {customers.length}
          </div>
          <div>
            <strong>Resolved:</strong>{" "}
            {customers.filter((c) => c.resolution_status === "Resolved").length}
          </div>
          <div>
            <strong>Pending:</strong>{" "}
            {customers.filter((c) => c.resolution_status === "Pending").length}
          </div>
          <div>
            <strong>Average Rating:</strong>{" "}
            {(
              customers.reduce((sum, c) => sum + c.feedback_rating, 0) /
              customers.length
            ).toFixed(1)}
          </div>
          <div>
            <strong>Positive Sentiment:</strong>{" "}
            {customers.filter((c) => c.user_sentiment === "Positive").length}
          </div>
        </div>
      </div>

      <div style={{ textAlign: "center", marginTop: "20px" }}>
        <a
          href="/"
          style={{
            display: "inline-block",
            padding: "10px 20px",
            backgroundColor: "#007bff",
            color: "white",
            textDecoration: "none",
            borderRadius: "5px",
            fontWeight: "500",
          }}
        >
          ← Back to Voice Agent
        </a>
      </div>
    </div>
  );
}
