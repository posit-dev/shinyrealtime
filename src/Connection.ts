export class Connection {
  private audioEl: HTMLAudioElement;
  private pc: RTCPeerConnection;
  private dc: RTCDataChannel;
  private micTrack: MediaStreamTrack;
  private eventListeners: Map<string, (data: any) => void>;
  private pendingSends: string[] = [];

  constructor(
    audioElement: HTMLAudioElement,
    peerConnection: RTCPeerConnection,
    dataChannel: RTCDataChannel,
    micTrack: MediaStreamTrack
  ) {
    this.audioEl = audioElement;
    this.pc = peerConnection;
    this.dc = dataChannel;
    this.micTrack = micTrack;
    this.eventListeners = new Map();

    // Flush any queued sends once the channel opens
    this.dc.addEventListener("open", () => {
      while (this.pendingSends.length > 0) {
        const payload = this.pendingSends.shift()!;
        try {
          this.dc.send(payload);
        } catch (err) {
          console.warn("Failed to flush queued event:", err);
        }
      }
    });

    // Set up data channel message handling
    this.dc.addEventListener("message", (e) => {
      // Notify all registered event listeners
      const data = e.data;
      // console.log("Received event:", data);

      // Dispatch event to all registered handlers
      this.eventListeners.forEach((callback) => {
        callback(data);
      });
    });
  }

  // Cleanup method to terminate the connection
  close(): void {
    console.log("Closing WebRTC connection");
    // Clean up tracks
    if (this.micTrack) {
      this.micTrack.stop();
    }
    // Close data channel
    if (this.dc) {
      this.dc.close();
    }
    // Close peer connection
    if (this.pc) {
      this.pc.close();
    }
  }

  // Volume property (0.0 - 1.0)
  get volume(): number {
    return this.audioEl.volume;
  }

  set volume(value: number) {
    this.audioEl.volume = Math.max(0, Math.min(1, value));
  }

  // Speaker muted property
  get audioMuted(): boolean {
    return this.audioEl.muted;
  }

  set audioMuted(value: boolean) {
    this.audioEl.muted = value;
  }

  // Microphone muted property
  get micMuted(): boolean {
    return !this.micTrack.enabled;
  }

  set micMuted(value: boolean) {
    this.micTrack.enabled = !value;
  }

  // Data channel method
  send(event: any): void {
    console.log("Sending event:", event);
    const payload = JSON.stringify(event);
    const state = this.dc.readyState;
    if (state === "open") {
      this.dc.send(payload);
    } else if (state === "connecting") {
      // Queue until "open" event flushes
      this.pendingSends.push(payload);
    } else {
      // "closing" or "closed" — channel gone, nothing we can do
      console.warn(
        `Dropping event; data channel readyState='${state}':`,
        event
      );
    }
  }

  addEventListener(id: string, callback: (data: any) => void): void {
    this.eventListeners.set(id, callback);
  }

  removeEventListener(id: string): void {
    this.eventListeners.delete(id);
  }

  // Expose elements for advanced use cases
  getAudioElement(): HTMLAudioElement {
    return this.audioEl;
  }

  getPeerConnection(): RTCPeerConnection {
    return this.pc;
  }

  getDataChannel(): RTCDataChannel {
    return this.dc;
  }

  getMicrophoneTrack(): MediaStreamTrack {
    return this.micTrack;
  }
}