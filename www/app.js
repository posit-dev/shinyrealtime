"use strict";
(() => {
  // src/MicButton.ts
  var _MicButton = class _MicButton {
    constructor(element, onMuteChange) {
      this.onMuteChange = onMuteChange;
      // ms to differentiate between click and hold
      // State
      this.muted = true;
      this.holdTimeout = null;
      this.pushToTalkActive = false;
      this.suppressNextClick = false;
      this.element = element;
      this.element.addEventListener("mousedown", () => this.startPress());
      this.element.addEventListener("touchstart", () => this.startPress());
      this.element.ownerDocument.addEventListener("keydown", (e) => {
        if (e.key === " " && !e.repeat) {
          e.preventDefault();
          this.startPress();
        }
      });
      this.element.addEventListener("mouseup", () => this.endPress());
      this.element.addEventListener("touchend", () => this.endPress());
      this.element.ownerDocument.addEventListener("keyup", (e) => {
        if (e.key === " ") {
          this.endPress();
        }
      });
      this.element.addEventListener("click", (e) => this.onClick(e));
    }
    /**
     * Getters & Setters
     */
    isMuted() {
      return this.muted;
    }
    isPushToTalkActive() {
      return this.pushToTalkActive;
    }
    setMuted(muted) {
      if (this.muted === muted) return;
      this.muted = muted;
      this.onMuteChange(muted);
    }
    /**
     * Push-to-talk methods. Call these only when we are sure the user is holding
     * the button or key down, not a momentary click/press.
     */
    startPushToTalk() {
      this.pushToTalkActive = true;
      this.setMuted(false);
    }
    stopPushToTalk() {
      if (this.pushToTalkActive) {
        this.pushToTalkActive = false;
        this.setMuted(true);
      }
    }
    /**
     * Toggle mute/unmute state
     */
    toggle() {
      this.setMuted(!this.muted);
    }
    /**
     * Begin the gesture that may turn out to be a click (toggle), or may turn out
     * to be a hold (push-to-talk).
     *
     * It's the same logic for mouse, touch, and space key.
     */
    startPress() {
      this.holdTimeout = window.setTimeout(() => {
        this.startPushToTalk();
        this.holdTimeout = null;
      }, _MicButton.HOLD_DELAY);
    }
    /**
     * End the gesture that may have been a click or a hold.
     */
    endPress() {
      this.suppressNextClick = true;
      window.setTimeout(() => {
        this.suppressNextClick = false;
      }, 0);
      if (this.holdTimeout) {
        clearTimeout(this.holdTimeout);
        this.holdTimeout = null;
        this.toggle();
      } else {
        this.stopPushToTalk();
      }
    }
    /**
     * We generally don't need this; it's only for programmatic clicks (e.g. from
     * screen readers, or possibly JS). We suppress it if it was preceded by a
     * mousedown/touchstart/keydown because we would've already performed the
     * desired action then.
     */
    onClick(e) {
      if (this.suppressNextClick) {
        e.preventDefault();
        e.stopImmediatePropagation();
        return;
      }
      this.toggle();
    }
  };
  // Constants
  _MicButton.HOLD_DELAY = 200;
  var MicButton = _MicButton;

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
    micTrack.enabled = false;
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
        const micButtonElement = el.querySelector(
          ".mic-toggle-btn"
        );
        const micButton = new MicButton(micButtonElement, (muted) => {
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
