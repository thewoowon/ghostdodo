/**
 * Sign-in.
 *
 * These cover the gap that made the report wizard unusable: the API required
 * a session and the web app had no way to start one. What matters here is
 * that a person can always reach a working door — the Google button is
 * offered only when the API can actually complete the flow, the email path
 * still works when it cannot, and a failed Google callback comes back with a
 * reason rather than a blank page.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SignInPage from "@/app/sign-in/page";
import { SignInPanel } from "@/components/auth/SignInPanel";

let calls: { url: string; init: RequestInit | undefined }[] = [];

function mockFetch(options: { google?: boolean; signInStatus?: number } = {}) {
  const { google = true, signInStatus = 202 } = options;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL, init?: RequestInit) => {
      const href = String(url);
      calls.push({ url: href, init });

      if (href.includes("/auth/providers")) {
        return new Response(JSON.stringify({ google, magic_link: true }), {
          status: 200,
        });
      }
      if (href.includes("/auth/sign-in")) {
        if (signInStatus !== 202) {
          return new Response(
            JSON.stringify({
              error: {
                code: "RATE_LIMITED",
                message: "요청이 너무 잦습니다.",
                request_id: "req-1",
                details: {},
              },
            }),
            { status: signInStatus },
          );
        }
        return new Response(
          JSON.stringify({ message: "보냈습니다.", dev_token: "dev-token-abc" }),
          { status: 202 },
        );
      }
      return new Response("{}", { status: 200 });
    }),
  );
}

beforeEach(() => {
  calls = [];
});

describe("SignInPanel", () => {
  it("offers Google when the server says it is configured", () => {
    mockFetch();
    render(<SignInPanel next="/report/new" callbackError={null} googleEnabled />);

    // Present on first render — no request from the browser decides it.
    const button = screen.getByRole("link", { name: /구글 계정으로 계속하기/ });
    // A full navigation to the API origin, not a fetch — the flow leaves the
    // app for Google and returns to the API's callback.
    expect(button.getAttribute("href")).toContain("/auth/google/start");
    // Where to land afterwards rides along.
    expect(button.getAttribute("href")).toContain(
      `next=${encodeURIComponent("/report/new")}`,
    );
    expect(calls.some((c) => c.url.includes("/auth/providers"))).toBe(false);
  });

  it("never renders the Google button when it is off, not even briefly", () => {
    // It used to render on first paint and vanish once the browser heard
    // back — and in production, with Google off, it always vanished.
    mockFetch();
    render(<SignInPanel next="/" callbackError={null} googleEnabled={false} />);

    expect(
      screen.queryByRole("link", { name: /구글 계정으로 계속하기/ }),
    ).not.toBeInTheDocument();
    // The email path is still there, so sign-in never becomes impossible.
    expect(screen.getByLabelText("이메일로 로그인")).toBeInTheDocument();
  });

  it("still offers the email path alongside Google", () => {
    mockFetch();
    render(<SignInPanel next="/" callbackError={null} googleEnabled />);

    expect(screen.getByRole("link", { name: /구글 계정으로 계속하기/ })).toBeInTheDocument();
    expect(screen.getByLabelText("이메일로 로그인")).toBeInTheDocument();
  });

  it("requests a magic link and confirms where it went", async () => {
    mockFetch();
    render(<SignInPanel next="/" callbackError={null} googleEnabled />);

    await userEvent.type(screen.getByLabelText("이메일로 로그인"), "dodo@example.com");
    await userEvent.click(screen.getByRole("button", { name: "링크 받기" }));

    expect(await screen.findByText(/dodo@example.com로 로그인 링크를 보냈습니다/))
      .toBeInTheDocument();

    const signIn = calls.find((c) => c.url.includes("/auth/sign-in"));
    expect(signIn?.init?.method).toBe("POST");
    expect(JSON.parse(String(signIn?.init?.body))).toEqual({
      email: "dodo@example.com",
    });
  });

  it("surfaces a rate limit in plain Korean rather than a code", async () => {
    mockFetch({ signInStatus: 429 });
    render(<SignInPanel next="/" callbackError={null} googleEnabled />);

    await userEvent.type(screen.getByLabelText("이메일로 로그인"), "dodo@example.com");
    await userEvent.click(screen.getByRole("button", { name: "링크 받기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "로그인 요청이 너무 잦습니다",
    );
  });

  it("explains why Google sent the user back", async () => {
    // The callback redirects here with a reason instead of rendering an
    // error envelope the browser would show as raw JSON.
    mockFetch();
    render(<SignInPanel next="/" callbackError="cancelled" googleEnabled />);

    expect(screen.getByRole("alert")).toHaveTextContent("구글 로그인이 취소되었습니다");
  });

  it("falls back to a generic reason for an unrecognized callback error", async () => {
    mockFetch();
    render(<SignInPanel next="/" callbackError="something-new" googleEnabled />);

    expect(screen.getByRole("alert")).toHaveTextContent("구글 로그인을 완료하지 못했습니다");
  });
});

describe("SignInPage", () => {
  // The page asks the API which providers exist before it renders, so the
  // panel's first paint is already the final one.
  async function renderPage() {
    render(await SignInPage({ searchParams: Promise.resolve({ next: "/me" }) }));
  }

  it("offers Google when the API has credentials", async () => {
    mockFetch({ google: true });
    await renderPage();

    expect(screen.getByRole("link", { name: /구글 계정으로 계속하기/ })).toBeInTheDocument();
  });

  it("leaves Google out when the API has none", async () => {
    mockFetch({ google: false });
    await renderPage();

    expect(
      screen.queryByRole("link", { name: /구글 계정으로 계속하기/ }),
    ).not.toBeInTheDocument();
  });

  it("still renders the email path when the API cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      }),
    );
    await renderPage();

    expect(
      screen.queryByRole("link", { name: /구글 계정으로 계속하기/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("이메일로 로그인")).toBeInTheDocument();
  });
});
