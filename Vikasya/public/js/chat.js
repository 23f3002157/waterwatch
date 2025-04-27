document.addEventListener("DOMContentLoaded", function () {
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const chatMessages = document.getElementById("chatMessages");
  const statusIndicator = document.getElementById("statusIndicator");
  const clearBtn = document.getElementById("clearBtn");
  const aboutLink = document.getElementById("aboutLink");

  // Focus the input field on page load
  messageInput.focus();

  // Handle chat form submission
  chatForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    messageInput.value = "";
    addMessage("user", message);

    statusIndicator.classList.remove("hidden");

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const data = await response.json();

      // Extract ONLY the response field content from the JSON
      const botReply = data.response
        ? data.response.trim()
        : "No response received.";

      // Add only the response text to the chat
      addMessage("bot", botReply);
    } catch (error) {
      console.error("Error:", error);
      addMessage("bot", `Error: ${error.message || "Something went wrong."}`);
    } finally {
      statusIndicator.classList.add("hidden");
      scrollToBottom();
      messageInput.focus();
    }
  });

  // Handle clear button click
  clearBtn.addEventListener("click", async function () {
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: "clear" }),
      });

      if (!response.ok) {
        throw new Error("Failed to clear chat");
      }

      // Clear the chat messages except for the welcome message
      while (chatMessages.children.length > 1) {
        chatMessages.removeChild(chatMessages.lastChild);
      }
    } catch (error) {
      console.error("Error clearing chat:", error);
    }
  });

  // Handle about link click
  aboutLink.addEventListener("click", function (e) {
    e.preventDefault();
    addMessage("user", "about");

    // Simulate API call for the about command
    statusIndicator.classList.remove("hidden");

    setTimeout(() => {
      const aboutResponse =
        "Community Water Watch Platform is an AI-powered system designed to help communities report and track water-related issues. You can report problems, get information about water quality, and learn best practices for water conservation.";
      addMessage("bot", aboutResponse);
      statusIndicator.classList.add("hidden");
      scrollToBottom();
    }, 500);
  });

  // Function to add a message to the chat
  function addMessage(type, text) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${
      type === "user" ? "user-message" : "bot-message"
    }`;

    // Format the message text
    let formattedText = text;

    // Convert markdown code blocks to HTML
    formattedText = formattedText.replace(
      /```(\w+)?\n([\s\S]*?)\n```/g,
      (match, language, code) => {
        return `<pre><code>${escapeHtml(code)}</code></pre>`;
      }
    );

    // Convert inline code to HTML
    formattedText = formattedText.replace(/`([^`]+)`/g, (match, code) => {
      return `<code>${escapeHtml(code)}</code>`;
    });

    // Convert line breaks to HTML
    formattedText = formattedText.replace(/\n\n/g, "</p><p>");
    formattedText = formattedText.replace(/\n/g, "<br>");

    // Get current time
    const now = new Date();
    const timeString = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas ${type === "user" ? "fa-user" : "fa-robot"}"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-name">${
                      type === "user" ? "You" : "WaterWatchBot"
                    }</span>
                    <span class="message-time">${timeString}</span>
                </div>
                <div class="message-text">
                    <p>${formattedText}</p>
                </div>
            </div>
          `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
  }

  // Helper function to escape HTML
  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Function to scroll to the bottom of the chat
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});
