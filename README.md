# TwitchChat
A simple, asynchronous Python 3 library for using Twitch chat with websockets.

## Dependencies
The only dependency this library has is the websocket-client library. Install easily with Pip:  
`pip install websocket-client`  
If you want to act on behalf of a Twitch account (for example, to send chat messages), then you'll also need to get an OAuth token.  
  
## Usage
The two use-cases for Twitch Chat are reading messages and sending messages. While you can do both at once, they're handled somewhat separately.  

### Send messages
First, create a Connection:  
`connection = chat.connect(username, oauth_token)`  
Then join a channel:  
`channel = connection.join_channel("adamcake")`  
A connection can be used to join multiple channels, but it is tied to the account used to create the connection.  
Send a message:  
`channel.send("Hello world!")`  

### Receive messages
Again, you must start by creating a Connection. But this time you'll specify a callback function:  
```
def message(m):
  print(m.message)
def notice(m):
  print(m.message)
def room_state(m):
  print(m.slow_mode)
connection = chat.connect(username, oauth_token, on_message=message, on_notice=notice, on_room_state=room_state)
```  
You can also connect to Twitch chat without signing in. In this mode, you'll be able to receive messages but not send them.  
`connection = chat.connect_as_guest(on_message=message, on_notice=notice, on_room_state=room_state)`  
After joining a channel with this connection, any received chat messages will be sent to your on_message function in a Message object. Any notices, such as "This room is now in slow mode", will be sent to your on_notice callback. Any changes in the room state, such as subscriber-only mode being enabled or disabled, will be sent to your on_room_state callback in a RoomState object. All of these are optional and may be set to None.  
  
Full list of Message parameters:  
`channel` - the channel name where the message was received, eg "adamcake"  
`message` - the text content of the message  
`badge_info` - a list of information about badges, for instance, the number of months they have been subscribed  
`badges` - list of badges the user should have next to their name  
`color` - Hex color of the user's display name, eg "#FF0000"  
`display_name` - the sender's display name  
`user_id` - the sender's User ID  
`user_type` - eg "mod" - usually blank  
`msg_id` - unique ID of this message assigned by Twitch  
`moderator` - whether the sender is a moderator  
`subscriber` - whether the sender is a subscriber  
`turbo` - whether the sender has Turbo (or Prime, I assume?)  
`timestamp` - unix timestamp in milliseconds for when the message was sent  
  
Notice parameters:  
`channel` - the channel name where the notice was received, eg "adamcake"  
`message` - the text content of the notice  
`msg_id` - unique ID of the message assigned by Twitch  
  
RoomState parameters:  
`channel` - the name of the channel which was updated  
`message` - the text content of the message  
`emote_only` - whether the channel is in emote-only mode  
`followers_only` - the minimum follow age for users to be able to chat, or -1 if followers-only mode is disabled  
`r9k` - whether the channel is in R9K mode  
`slow` - the cooldown period, in seconds, that is required between messages  
`subscribers_only` - whether the channel is in subscribers-only mode  

### Misc
If you want to leave a channel, you can do so:  
`channel.leave()`  
And finally, to permanently close a connection:  
`connection.disconnect()`  
Note that leaving a channel invalidates the `Channel` object it was called on. Disconnecting a `Connection` invalidates that object as well as all `Channel` objects created with it.
