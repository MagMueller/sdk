import type { HttpClient } from "../../core/http.js";
import type { components } from "../../generated/v4/types.js";

type BrowserSessionView = components["schemas"]["BrowserSessionView"];

export class Browsers {
  constructor(private readonly http: HttpClient) {}

  /** Stop a browser session and refund its unused time. */
  stop(sessionId: string): Promise<BrowserSessionView> {
    return this.http.patch<BrowserSessionView>(`/browsers/${sessionId}`, {
      action: "stop",
    });
  }
}
