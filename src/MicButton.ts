/**
 * MicButton - Abstracts microphone button state management
 * 
 * Manages state for mute/unmute and push-to-talk functionality
 */
export class MicButton {
  // Constants
  static readonly HOLD_DELAY = 200; // ms to differentiate between click and hold

  // State
  private muted: boolean = true;
  private holdTimeout: number | null = null;
  private pushToTalkActive: boolean = false;
  private suppressNextClick: boolean = false;

  // DOM elements
  private element: HTMLElement;

  constructor(
    element: HTMLElement,
    private onMuteChange: (muted: boolean) => void
  ) {
    this.element = element;

    // Add event handlers
    this.element.addEventListener("mousedown", () => this.startPress());
    this.element.addEventListener("touchstart", () => this.startPress());
    this.element.ownerDocument.addEventListener("keydown", (e) => {
      if (e.key === " " && !e.repeat) {
        e.preventDefault(); // Prevent page scrolling
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
  public isMuted(): boolean {
    return this.muted;
  }

  public isPushToTalkActive(): boolean {
    return this.pushToTalkActive;
  }

  public setMuted(muted: boolean): void {
    if (this.muted === muted) return;

    this.muted = muted;
    this.onMuteChange(muted);
  }

  /**
   * Push-to-talk methods. Call these only when we are sure the user is holding
   * the button or key down, not a momentary click/press.
   */
  public startPushToTalk(): void {
    this.pushToTalkActive = true;
    this.setMuted(false);
  }

  public stopPushToTalk(): void {
    if (this.pushToTalkActive) {
      this.pushToTalkActive = false;
      this.setMuted(true);
    }
  }

  /**
   * Toggle mute/unmute state
   */
  public toggle(): void {
    this.setMuted(!this.muted);
  }

  /**
   * Begin the gesture that may turn out to be a click (toggle), or may turn out
   * to be a hold (push-to-talk).
   *
   * It's the same logic for mouse, touch, and space key.
   */
  private startPress(): void {
    // Do nothing at first--we don't know if it's a click or hold
    this.holdTimeout = window.setTimeout(() => {
      this.startPushToTalk();
      this.holdTimeout = null;
    }, MicButton.HOLD_DELAY);
  }

  /**
   * End the gesture that may have been a click or a hold.
   */
  private endPress(): void {
    this.suppressNextClick = true;
    window.setTimeout(() => {
      this.suppressNextClick = false;
    }, 0);

    if (this.holdTimeout) {
      // It was a click
      clearTimeout(this.holdTimeout);
      this.holdTimeout = null;
      this.toggle();
    } else {
      // It was a hold
      this.stopPushToTalk();
    }
  }

  /**
   * We generally don't need this; it's only for programmatic clicks (e.g. from
   * screen readers, or possibly JS). We suppress it if it was preceded by a
   * mousedown/touchstart/keydown because we would've already performed the
   * desired action then.
   */
  private onClick(e: MouseEvent): void {
    if (this.suppressNextClick) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }
    this.toggle();
  }
}
