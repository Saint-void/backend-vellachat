# Conversation Expiry Implementation

## Overview

Conversations automatically expire after 30 minutes of inactivity. This creates a clean chat experience where users ask questions, get answers, and move on. After expiry, users click "Refresh" to start a fresh conversation. **All messages are archived in the database** but not displayed in the UI.

## How It Works

### 1. Expiry States

- **`open`**: Active conversation, accepting new messages
- **`closed`**: Explicitly closed by the client
- **`expired`**: Automatically marked as expired after 30 minutes of inactivity (read-only)

### 2. Automatic Expiry (Background Task)

The `expire_inactive_conversations()` task marks conversations as expired if they haven't been updated in 30 minutes.

**Implementation**: See [app/widget/widgetTasks.py](app/widget/widgetTasks.py)

**To run the expiry task**, call it from your deployment's cron job or scheduler:

```python
from app.widget.widgetTasks import expire_inactive_conversations

# Run every 5 minutes (for example)
await expire_inactive_conversations(timeout_minutes=30)
```

Or directly in Python:

```bash
python -c "
import asyncio
from app.widget.widgetTasks import expire_inactive_conversations

count = asyncio.run(expire_inactive_conversations(timeout_minutes=30))
print(f'Marked {count} conversations as expired')
"
```

### 3. Access to Expired Conversations

- **Read**: ✅ Allowed - Users can view conversation history
- **Send Messages**: ❌ Blocked - Returns error: "This conversation has expired. Start a new one by refreshing."

### 4. Refresh Button (Start New Conversation)

Users can start a new conversation anytime by clicking the "Refresh" button in the chat widget. This creates a new conversation thread without waiting for the 30-minute expiry:

```javascript
// Frontend: Refresh button handler
async function refreshChat() {
  // Create a brand new conversation
  const response = await fetch(`/api/v1/widget/${chatbotId}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      site_origin: window.location.origin,
      visitor_id: visitorId, // same visitor, new conversation
    }),
  });
  const newConversation = await response.json();
  // Switch UI to new conversation
  switchConversation(newConversation);
}
```

### 5. Explicit Close (Client-Initiated)

Clients can close conversations explicitly via:

```http
POST /api/v1/widget/{chatbot_id}/conversations/{conversation_id}/close?site_origin=example.com
```

Response: Updated conversation with `status: "closed"` and `updated_at` timestamp.

## Database Schema

No schema changes required. The existing `updated_at` timestamp on `WidgetConversation` is used to track inactivity:

```python
class WidgetConversation(Base):
    status: str = "open"  # "open" | "closed" | "expired"
    updated_at: datetime  # Updated when message is sent, used for inactivity tracking
```

## Testing

Run the expiry tests:

```bash
pytest tests/test_widget_expiry.py -v
```

Tests verify:

- ✅ Expired conversations CAN be read (for viewing history)
- ❌ Expired conversations CANNOT receive new messages (returns ValidationError)

## Frontend Integration

### 1. Show "Refresh" Button When Expired

When the user tries to send a message to an expired conversation, they get a 400 error. Show the refresh button at that point:

```javascript
try {
  await sendMessage(conversationId, userMessage);
} catch (error) {
  if (error.message.includes("expired")) {
    showRefreshButton(); // "Start New Chat" button
  }
}
```

### 2. Refresh Button Handler

When user clicks "Start New Chat", create a brand new conversation and clear the old messages:

```javascript
async function startNewChat() {
  const response = await fetch(`/api/v1/widget/${chatbotId}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      site_origin: window.location.origin,
      visitor_id: visitorId,
    }),
  });
  const newConversation = await response.json();

  // Fresh start
  clearAllMessages();
  currentConversationId = newConversation.id;
  focusInput();
  showGreetingMessage(); // show chatbot greeting again
}
```

## Deployment Integration

### Option 1: Cron Job (Recommended for simplicity)

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/backend && python -c "import asyncio; from app.widget.widgetTasks import expire_inactive_conversations; asyncio.run(expire_inactive_conversations())"
```

### Option 2: Scheduled Task in FastAPI (Future Enhancement)

Use APScheduler to run cleanup on app startup:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.widget.widgetTasks import expire_inactive_conversations

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(expire_inactive_conversations, 'interval', minutes=5)
    scheduler.start()
```

## Benefits

1. **Clean Chat Experience**: Fresh start every 30 mins - users don't scroll through old conversations
2. **Data Preservation**: All messages archived in database (audit trail, no data loss)
3. **Reduced Server Load**: Old conversations marked as expired, not repeatedly loaded
4. **Simple UX**: One "Refresh" button to start over - no complexity, no history sidebar
