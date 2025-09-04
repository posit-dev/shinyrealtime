import "./binding";
import { Connection } from "./Connection";
import { MicButton } from "./MicButton";
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

  // Start the session using the Session Description Protocol (SDP)
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const baseUrl = "https://api.openai.com/v1/realtime/calls";
  const model = "gpt-realtime";
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

  // Create and return the connection instance
  return new Connection(audioEl, pc, dc, micTrack);
}

// Custom Shiny output binding for real-time display
class RealtimeBinding extends Shiny.OutputBinding {
  find(scope) {
    return $(scope).find(".shinyrealtime");
  }

  renderValue(el, data) {
    const id = this.getId(el);

    // Store connection in element data for cleanup
    let connectionPromise = openConnection(data).then((connection) => {
      $(document).on("shiny:disconnected", function () {
        console.log("Shiny disconnected, cleaning up any WebRTC connections");
        connection.close();
      });

      // MicButton implementation has been moved to MicButton.ts

      // Create the mic button controller
      const micButtonElement = el.querySelector(
        ".mic-toggle-btn"
      ) as HTMLElement;
      const micButton = new MicButton(micButtonElement, (muted: boolean) => {
        // This is our callback when mic state changes
        connection.micMuted = muted;

        if (muted) {
          micButtonElement.classList.remove("active", "btn-danger");
          micButtonElement.classList.add("btn-secondary");
        } else {
          micButtonElement.classList.remove("btn-secondary");
          micButtonElement.classList.add("active", "btn-danger");
        }
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
  }

  // Clean up connection when element is removed/updated
  unsubscribe(el) {
    const connection = $(el).data("rtConnection");
    if (connection && typeof connection.close === "function") {
      console.log("Closing WebRTC connection due to element unsubscribe");
      connection.close();
    }
  }
}

// Register the binding
Shiny.outputBindings.register(new RealtimeBinding(), "realtime-output");

// Plays audio elements, identified by CSS selector
Shiny.addCustomMessageHandler(
  "play_audio",
  ({ selector }: { selector: string }) => {
    const audioEl = document.querySelector(selector) as HTMLAudioElement;
    if (audioEl) {
      audioEl.currentTime = 0;
      audioEl.play().catch((err) => {
        console.error("Error playing audio:", err);
      });
    } else {
      console.error("Audio element not found for selector:", selector);
    }
  }
);