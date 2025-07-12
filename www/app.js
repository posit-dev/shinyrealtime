"use strict";
(() => {
  // src/index.ts
  async function openConnection(ephemeralKey) {
    const pc = new RTCPeerConnection();
    const audioEl = document.createElement("audio");
    audioEl.autoplay = true;
    pc.ontrack = (e) => audioEl.srcObject = e.streams[0];
    const ms = await navigator.mediaDevices.getUserMedia({
      audio: true
    });
    const micTrack = ms.getTracks()[0];
    pc.addTrack(micTrack);
    const dc = pc.createDataChannel("oai-events");
    const eventListeners = /* @__PURE__ */ new Map();
    dc.addEventListener("message", (e) => {
      const data = e.data;
      console.log("Received event:", data);
      eventListeners.forEach((callback) => {
        callback(data);
      });
    });
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    const baseUrl = "https://api.openai.com/v1/realtime";
    const model = "gpt-4o-realtime-preview-2025-06-03";
    const sdpResponse = await fetch(`${baseUrl}?model=${model}`, {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${ephemeralKey}`,
        "Content-Type": "application/sdp"
      }
    });
    const answer = {
      type: "answer",
      sdp: await sdpResponse.text()
    };
    await pc.setRemoteDescription(answer);
    const connection = {
      // Cleanup method to terminate the connection
      close: () => {
        console.log("Closing WebRTC connection");
        if (micTrack) {
          micTrack.stop();
        }
        if (dc) {
          dc.close();
        }
        if (pc) {
          pc.close();
        }
      },
      // Volume property (0.0 - 1.0)
      get volume() {
        return audioEl.volume;
      },
      set volume(value) {
        audioEl.volume = Math.max(0, Math.min(1, value));
      },
      // Speaker muted property
      get audioMuted() {
        return audioEl.muted;
      },
      set audioMuted(value) {
        audioEl.muted = value;
      },
      // Microphone muted property
      get micMuted() {
        return !micTrack.enabled;
      },
      set micMuted(value) {
        micTrack.enabled = !value;
      },
      // Data channel method
      send: (event) => {
        console.log("Sending event:", event);
        dc.send(JSON.stringify(event));
      },
      addEventListener: (id, callback) => {
        eventListeners.set(id, callback);
      },
      removeEventListener: (id) => {
        eventListeners.delete(id);
      },
      // Expose elements for advanced use cases
      getAudioElement: () => audioEl,
      getPeerConnection: () => pc,
      getDataChannel: () => dc,
      getMicrophoneTrack: () => micTrack
    };
    return connection;
  }
  var realtimeBinding = new Shiny.OutputBinding();
  $.extend(realtimeBinding, {
    find: function(scope) {
      return $(scope).find(".shinyrealtime");
    },
    renderValue: function(el, data) {
      const id = this.getId(el);
      let connectionPromise = openConnection(data).then((connection) => {
        $(document).on("shiny:disconnected", function() {
          console.log("Shiny disconnected, cleaning up any WebRTC connections");
          connection.close();
        });
        $(el).find(".btn-mute").show();
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
        connection.addEventListener("shiny", (data2) => {
          Shiny.setInputValue(id + "_event", data2, { priority: "event" });
        });
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
    unsubscribe: function(el) {
      const connection = $(el).data("rtConnection");
      if (connection && typeof connection.close === "function") {
        console.log("Closing WebRTC connection due to element unsubscribe");
        connection.close();
      }
    }
  });
  Shiny.outputBindings.register(realtimeBinding, "realtime-output");
})();
//# sourceMappingURL=app.js.map
