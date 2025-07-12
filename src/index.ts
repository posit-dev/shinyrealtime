import "./binding";
import "./styles.css";

export async function openConnection(ephemeralKey: string) {
  // Create a peer connection
  const pc = new RTCPeerConnection();

  // Set up to play remote audio from the model
  const audioEl = document.createElement("audio");
  audioEl.autoplay = true;

  pc.ontrack = (e) => (audioEl.srcObject = e.streams[0]);

  // Add local audio track for microphone input in the browser
  const ms = await navigator.mediaDevices.getUserMedia({
    audio: true,
  });
  const micTrack = ms.getTracks()[0];
  pc.addTrack(micTrack);
  micTrack.enabled = false; // Start with mic muted

  // Set up data channel for sending and receiving events
  const dc = pc.createDataChannel("oai-events");

  // Event listeners for data channel
  const eventListeners = new Map();

  dc.addEventListener("message", (e) => {
    // Notify all registered event listeners
    const data = e.data;
    console.log("Received event:", data);

    // Dispatch event to all registered handlers
    eventListeners.forEach((callback) => {
      callback(data);
    });
  });

  // Start the session using the Session Description Protocol (SDP)
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const baseUrl = "https://api.openai.com/v1/realtime";
  const model = "gpt-4o-realtime-preview-2025-06-03";
  const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
    method: "POST",
    body: offer.sdp,
    headers: {
      Authorization: `Bearer ${ephemeralKey}`,
      "Content-Type": "application/sdp",
    },
  });

  const answer: RTCSessionDescriptionInit = {
    type: "answer",
    sdp: await sdpResponse.text(),
  };
  await pc.setRemoteDescription(answer);

  // Create the connection object with getters/setters for properties
  const connection = {
    // Cleanup method to terminate the connection
    close: () => {
      console.log("Closing WebRTC connection");
      // Clean up tracks
      if (micTrack) {
        micTrack.stop();
      }
      // Close data channel
      if (dc) {
        dc.close();
      }
      // Close peer connection
      if (pc) {
        pc.close();
      }
    },

    // Volume property (0.0 - 1.0)
    get volume() {
      return audioEl.volume;
    },
    set volume(value: number) {
      audioEl.volume = Math.max(0, Math.min(1, value));
    },

    // Speaker muted property
    get audioMuted() {
      return audioEl.muted;
    },
    set audioMuted(value: boolean) {
      audioEl.muted = value;
    },

    // Microphone muted property
    get micMuted() {
      return !micTrack.enabled;
    },
    set micMuted(value: boolean) {
      micTrack.enabled = !value;
    },

    // Data channel method
    send: (event: any) => {
      console.log("Sending event:", event);
      dc.send(JSON.stringify(event));
    },
    addEventListener: (id: string, callback: (data: any) => void) => {
      eventListeners.set(id, callback);
    },
    removeEventListener: (id: string) => {
      eventListeners.delete(id);
    },

    // Expose elements for advanced use cases
    getAudioElement: () => audioEl,
    getPeerConnection: () => pc,
    getDataChannel: () => dc,
    getMicrophoneTrack: () => micTrack,
  };

  return connection;
}

// Custom Shiny output binding for real-time display
var realtimeBinding = new Shiny.OutputBinding();

$.extend(realtimeBinding, {
  find: function (scope) {
    return $(scope).find(".shinyrealtime");
  },

  renderValue: function (el, data) {
    const id = this.getId(el);

    // Store connection in element data for cleanup
    let connectionPromise = openConnection(data).then((connection) => {
      $(document).on("shiny:disconnected", function () {
        console.log("Shiny disconnected, cleaning up any WebRTC connections");
        connection.close();
      });

      $(el).find(".btn-unmute").show();
      $(el).on("click", ".btn-mute", () => {
        connection.micMuted = true;
        $(el).find(".btn-mute").hide();
        $(el).find(".btn-unmute").show();
      });
      $(el).on("click", ".btn-unmute", () => {
        connection.micMuted = false;
        $(el).find(".btn-unmute").hide();
        $(el).find(".btn-mute").show();
      });

      $(el).data("rtConnection", connection);

      // Set up Shiny-specific event handling
      connection.addEventListener("shiny", (data) => {
        Shiny.setInputValue(id + "_event", data, { priority: "event" });
      });

      // Set up message handler for sending events from Shiny
      Shiny.addCustomMessageHandler("realtime_send", (events) => {
        if (Array.isArray(events)) {
          events.forEach((event) => connection.send(event));
        } else {
          connection.send(events);
        }
      });

      return connection;
    });
  },

  // Clean up connection when element is removed/updated
  unsubscribe: function (el) {
    const connection = $(el).data("rtConnection");
    if (connection && typeof connection.close === "function") {
      console.log("Closing WebRTC connection due to element unsubscribe");
      connection.close();
    }
  },
});

// Register the binding
Shiny.outputBindings.register(realtimeBinding, "realtime-output");
