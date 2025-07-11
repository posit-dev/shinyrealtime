import "./binding";
import "./styles.css";

export async function openConnection(id: string, ephemeralKey: string) {
  // Create a peer connection
  const pc = new RTCPeerConnection();

  // Set up to play remote audio from the model
  const audioEl = document.createElement("audio");
  audioEl.autoplay = true;
  // audioEl.muted = true;
  pc.ontrack = (e) => (audioEl.srcObject = e.streams[0]);

  // Add local audio track for microphone input in the browser
  const ms = await navigator.mediaDevices.getUserMedia({
    audio: true,
  });
  const micTrack = ms.getTracks()[0];
  // micTrack.enabled = false;
  pc.addTrack(micTrack);

  // Set up data channel for sending and receiving events
  const dc = pc.createDataChannel("oai-events");
  dc.addEventListener("message", (e) => {
    // Realtime server events appear here!
    console.log(e);
    Shiny.setInputValue(id + "_event", e.data, { priority: "event" });
  });

  Shiny.addCustomMessageHandler("realtime_send", (events) => {
    for (const event of events) {
      console.log("Sending event:", event);
      dc.send(JSON.stringify(event));
    }
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
}

// Custom Shiny output binding for real-time display
var realtimeBinding = new Shiny.OutputBinding();

$.extend(realtimeBinding, {
  find: function (scope) {
    return $(scope).find(".shinyrealtime");
  },

  renderValue: function (el, data) {
    openConnection(this.getId(el), data);
  },
});

// Register the binding
Shiny.outputBindings.register(realtimeBinding, "realtime-output");
