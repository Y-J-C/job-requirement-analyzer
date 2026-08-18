import { afterEach, describe, expect, it, vi } from "vitest";

import { applicationFetch } from "./api-client";


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("applicationFetch", () => {
  it("forwards a request without adding an authorization header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null));
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request("http://localhost:8000/api/v1/target-roles", {
      method: "POST",
      body: "payload",
    });

    await applicationFetch(request);

    const sent = fetchMock.mock.calls[0][0] as Request;
    expect(sent.headers.has("authorization")).toBe(false);
    expect(await sent.text()).toBe("payload");
  });
});
